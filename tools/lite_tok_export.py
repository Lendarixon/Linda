"""Copy a Lite model and append linear token scores without changing z.

Usage: python tools/lite_tok_export.py SRC_DIR OUT_DIR
"""
from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"

import numpy as np
import onnx
from onnx import helper, numpy_helper

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def add_tok(model):
    graph = model.graph
    if any(o.name == "tok" for o in graph.output):
        raise ValueError("Source already has a tok output")
    producers = {o: node for node in graph.node for o in node.output}
    constants = {i.name: numpy_helper.to_array(i) for i in graph.initializer}

    def value(name):
        if name in constants:
            return constants[name]
        node = producers[name]
        attrs = {a.name: helper.get_attribute_value(a) for a in node.attribute}
        if node.op_type == "Constant":
            return numpy_helper.to_array(attrs["value"])
        if node.op_type == "Cast":
            return value(node.input[0]).astype(helper.tensor_dtype_to_np_dtype(attrs["to"]))
        if node.op_type == "Identity":
            return value(node.input[0])
        raise ValueError(f"Unsupported constant producer: {node.op_type} ({name})")

    node = producers["z"]
    while node.op_type in ("Identity", "Cast", "Squeeze", "Reshape"):
        node = producers[node.input[0]]
    if node.op_type != "Slice":
        raise ValueError("Expected z to retain one Gemm column through Slice")
    starts, ends = value(node.input[1]).ravel(), value(node.input[2]).ravel()
    axes = value(node.input[3]).ravel() if len(node.input) > 3 and node.input[3] else np.arange(len(starts))
    steps = value(node.input[4]).ravel() if len(node.input) > 4 and node.input[4] else np.ones(len(starts), dtype=int)
    gemm = producers[node.input[0]]
    if gemm.op_type != "Gemm":
        raise ValueError("Expected Slice input to be Gemm")
    attrs = {a.name: helper.get_attribute_value(a) for a in gemm.attribute}
    if attrs.get("transA", 0):
        raise ValueError("transA Gemm is unsupported")
    weight = value(gemm.input[1])
    if attrs.get("transB", 0):
        weight = weight.T
    columns = np.arange(weight.shape[1])
    for st, en, ax, step in zip(starts, ends, axes, steps):
        if int(ax) in (1, -1):
            columns = columns[slice(int(st), int(en), int(step))]
        elif int(ax) != 0 or int(st) != 0 or int(step) != 1 or int(en) < 2**31 - 1:
            raise ValueError("Slice must preserve every batch row")
    if len(columns) != 1:
        raise ValueError("Slice must retain exactly one head column")
    k = int(columns[0])
    w = np.asarray(weight[:, k] * attrs.get("alpha", 1.0), dtype=weight.dtype)
    bias = np.broadcast_to(value(gemm.input[2]), (weight.shape[1],))
    b = np.asarray(bias[k] * attrs.get("beta", 1.0), dtype=weight.dtype)
    hidden = "/enc/encoder/layer.11/output/LayerNorm/LayerNormalization_output_0"
    if hidden not in producers:
        raise ValueError("Last encoder hidden state is absent")
    names = set(producers) | set(constants) | {i.name for i in graph.input}
    if names & {"tok", "lite_tok_weight", "lite_tok_bias", "lite_tok_dot"}:
        raise ValueError("Token branch names collide with the original graph")
    original_nodes = [n.SerializeToString() for n in graph.node]
    graph.initializer.extend([numpy_helper.from_array(w, "lite_tok_weight"),
                              numpy_helper.from_array(b, "lite_tok_bias")])
    graph.node.extend([
        helper.make_node("MatMul", [hidden, "lite_tok_weight"], ["lite_tok_dot"], name="lite_tok_matmul"),
        helper.make_node("Add", ["lite_tok_dot", "lite_tok_bias"], ["tok"], name="lite_tok_add"),
    ])
    dtype = helper.np_dtype_to_tensor_dtype(w.dtype)
    graph.output.append(helper.make_tensor_value_info("tok", dtype, ["batch", "seq"]))
    assert original_nodes == [n.SerializeToString() for n in graph.node[:len(original_nodes)]]
    onnx.checker.check_model(model)
    return model, k


def verify(src, dst):
    import onnxruntime as ort
    from linda_pro.voters import SpeedOnnx

    voter = SpeedOnnx(src, threads=4, batch=4)
    voter._load()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    # Sessions run sequentially; both use CPU only.
    session = ort.InferenceSession(str(dst / "model.onnx"), options,
                                  providers=["CPUExecutionProvider"])
    rnd = random.Random(7)
    words = "the forest study people evidence explain tomorrow unusual beautiful sentence question answer world computer research".split()
    texts = [" ".join(rnd.choices(words, k=rnd.randint(1, 400))) for _ in range(20)]
    ids_list = [[voter.tok.token_to_id("<s>"), *e.ids[:voter.max_len - 2],
                 voter.tok.token_to_id("</s>")]
                for e in voter.tok.encode_batch(texts, add_special_tokens=False)]
    z_diff = mean_diff = 0.0
    identical = True
    for offset in range(0, len(ids_list), 4):
        seqs = ids_list[offset:offset + 4]
        width = max(map(len, seqs))
        ids = np.full((len(seqs), width), voter.tok.token_to_id("<pad>"), dtype=np.int64)
        mask = np.zeros_like(ids)
        for row, seq in enumerate(seqs):
            ids[row, :len(seq)] = seq
            mask[row, :len(seq)] = 1
        if voter.vmap is not None:
            ids = voter.vmap[ids].astype(np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        original = voter.sess.run(["z"], feed)[0]
        z, tok = session.run(["z", "tok"], feed)
        if not all(np.isfinite(a).all() for a in (original, z, tok)):
            raise ValueError("Verification produced non-finite scores")
        identical &= np.array_equal(original, z)
        z_diff = max(z_diff, float(np.max(np.abs(original - z))))
        mean = (tok.astype(np.float64) * mask).sum(axis=1) / mask.sum(axis=1)
        mean_diff = max(mean_diff, float(np.max(np.abs(mean - z[:, 0]))))
    passed = identical and np.isfinite(z_diff) and np.isfinite(mean_diff) and z_diff < 1e-4 and mean_diff < 1e-3
    print(f"{'PASS' if passed else 'FAIL'} texts=20 z_max_diff={z_diff:.9g} "
          f"tok_mean_max_diff={mean_diff:.9g} z_bit_identical={identical}", flush=True)
    voter.close()
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    try:
        src, dst = args.src_dir.resolve(), args.out_dir.resolve()
        if src == dst or src in dst.parents or dst in src.parents:
            raise ValueError("Source and destination must be separate folders")
        if dst.exists() and not dst.is_dir():
            raise ValueError("Destination must be a folder")
        model, column = add_tok(onnx.load(str(src / "model.onnx")))
        # Rebuild from the source on every run, including after a partial export.
        # Merge into an existing output folder without deleting unrelated files.
        shutil.copytree(src, dst, dirs_exist_ok=True)
        onnx.save(model, str(dst / "model.onnx"))
        print(f"Exported tok from head column {column}: {dst}", flush=True)
        return 0 if verify(src, dst) else 1
    except Exception as exc:
        print(f"FAIL {type(exc).__name__}: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
