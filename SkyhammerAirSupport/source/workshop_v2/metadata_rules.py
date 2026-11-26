"""Validate titles and description footers before any Workshop submission."""
import re

def validate_metadata(config, item, modid, stage_title, descriptions):
    errors=[]
    if config.get('item_id')!=item or config.get('mod_id')!=modid:
        errors.append('metadata configuration does not match the Workshop item/mod')
    titles=config.get('titles',{})
    for lang in ('english','koreana'):
        title=titles.get(lang,'')
        if not title.strip() or len(title.encode('utf-8'))>128:
            errors.append(lang+' title missing or over 128 UTF-8 bytes')
        if lang=='koreana' and not re.search('[가-힣]',title):
            errors.append('Korean title has no Korean text')
        description=descriptions.get(lang,'').replace('\r\n','\n').rstrip('\n')
        footer=f'Workshop ID: {item}\nMod ID: {modid}'
        if not description.endswith(footer) or description.count('Workshop ID:')!=1 or description.count('Mod ID:')!=1:
            errors.append(lang+' footer missing, duplicated or mismatched')
        if len(description.replace('\n','\r\n').encode('utf-8'))>=8000:
            errors.append(lang+' description exceeds the UTF-8 byte limit')
    if titles.get('english')!=stage_title:
        errors.append('English title does not match workshop.txt')
    return errors
