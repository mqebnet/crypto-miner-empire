ES = {"es","es-es","es-mx","es-ar","es-co","es-cl","es-pe","es-ve"}
def detect_lang(code):
    if not code: return "es"
    return "es" if code.lower().replace("_","-") in ES else "en"
