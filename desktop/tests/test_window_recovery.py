from linda_desktop.window_recovery import RestoreState

def test_restore_schedules_once_without_ordinary_resize_repaint():
    state=RestoreState()
    assert not state.changed(False)
    assert not state.changed(True)
    assert state.changed(False)
    assert not state.changed(False)
    assert state.take(False,False)
    assert not state.take(False,False)

def test_minimize_again_cancels_old_restore():
    state=RestoreState()
    state.changed(True);state.changed(False);state.changed(True)
    assert not state.take(True,False)
    assert state.changed(False)
    assert state.take(False,False)

def test_closed_host_is_never_repainted():
    state=RestoreState()
    state.changed(True);state.changed(False)
    assert not state.take(False,True)
