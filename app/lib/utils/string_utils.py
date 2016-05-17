import types 
import unicodedata

def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def is_integer(value):
    try:
        return str(int(value)) == str(value)
    except ValueError:
        return False

def remove_accents(value):
    if type(value) is types.UnicodeType:
        return_value = value
    else:
        return_value = unicode(value, 'utf-8')
    return_value = return_value \
        .replace(u'\u2019', u'\'') \
        .replace(u'\u201C', u'"') \
        .replace(u'\u201D', u'"') \
        .replace(u'\221E', u' ') \
        .replace(u'\u2032', u"'") \
        .replace(u'\u221e', u" ") \
        .replace(u'\u200e', u"") \
        .replace(u'\u2205', u'0')
    nkfd_form = unicodedata.normalize('NFKD', return_value)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

def slugify(value, slug_char="-"):
    value = value.replace("&", " and ")
    value = remove_accents(value)
    slugified = ""
    for i in range(0, len(value)):
        char = value[i]
        if char.isalpha() or is_number(char):
            slugified += char
        else:
            if slugified and slugified[-1] != slug_char:
                slugified += slug_char
    if slugified.endswith(slug_char):
        slugified = slugified[:-1]
    return slugified

def unicode_urlencode(value, safe=""):
    import urllib
    safe += "/"
    value = remove_accents(value)
    if type(value) is types.UnicodeType:
        return urllib.quote_plus(value.encode("utf-8"), safe=safe) 
    else:
        return urllib.quote_plus(value, safe=safe)
