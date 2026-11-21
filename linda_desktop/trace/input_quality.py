"""Conservative input suitability hints, not language detection or efficacy claims."""
import re


def quality_warnings(documents, language):
    flagged_lists, flagged_script = [], []
    for doc in documents:
        text = doc.get('text', '')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        listed = sum(bool(re.match(r'^(?:[-*•]|\d+[.)])\s', line)) for line in lines)
        if len(lines) >= 8 and listed / len(lines) >= 0.4:
            flagged_lists.append(str(doc.get('title') or doc.get('id'))[:80])
        latin = len(re.findall(r'[A-Za-zÀ-ž]', text))
        cyrillic = len(re.findall(r'[А-Яа-яЁё]', text))
        if latin+cyrillic >= 100 and ((language == 'ru' and latin > 2*cyrillic) or
                                     (language in ('en', 'pl') and cyrillic > 2*latin)):
            flagged_script.append(str(doc.get('title') or doc.get('id'))[:80])
    warnings = []
    if flagged_lists:
        message = {'ru': 'Много списков или пунктов: сравнение может быть ненадёжным',
                   'en': 'List-heavy text: style comparison may be unreliable',
                   'pl': 'Tekst zawiera wiele list: porównanie może być niewiarygodne'}[language]
        warnings.append(message + ': ' + ', '.join(flagged_lists[:5]) + (f' (+{len(flagged_lists)-5})' if len(flagged_lists)>5 else ''))
    if flagged_script:
        message = {'ru': 'Письменность не соответствует выбранному языку; проверьте язык корпуса',
                   'en': 'The script differs from the selected language; check the corpus language',
                   'pl': 'Pismo nie odpowiada wybranemu językowi; sprawdź język korpusu'}[language]
        warnings.append(message + ': ' + ', '.join(flagged_script[:5]) + (f' (+{len(flagged_script)-5})' if len(flagged_script)>5 else ''))
    return warnings
