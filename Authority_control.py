import pywikibot
from pywikibot import pagegenerators, textlib
import json
import re

AUTHORITY_CONTROL_ID = {268, 214, 7859, 3372, 6804, 1907, 4186, 2092, 1908, 1707, 6829, 2349, 6792, 227, 1960, 347, 1248, 244, 1225, 2041, 409, 2750, 650, 350, 781, \
                        3430, 3544, 1315, 245, 1986, 7902, 651, 791, 7303, 3563, 4055, 3223, 4423, 3723, 3993, 3562, 2980, 4038, 3920, 4143, 3863, 3601, 902, 886, \
                        3065, 781, 1362, 691, 1890, 950, 9984, 3348, 1375, 8189, 1736, 396, 3863, 1986, 8034, 349, 271, 5034, 1368, 651, 1006, 650, 350, 1695, 7293, 1003, \
                        947, 906, 5587, 7314, 1048, 2558}

def save(site, page, text:str, summary:str = "", add:bool = False, minor:bool = True, max_retry_times:int = 3):
    e = None
    oringinal_text = ""
    if add and page.exists():
        oringinal_text = page.get(force = True, get_redirect = True)
    for _ in range(max_retry_times):
        try:
            if add and page.exists():
                page.text = textlib.add_text(oringinal_text, text, site = site)
            else:
                page.text = text
            page.save(summary, minor = minor)
            return True
        except pywikibot.exceptions.EditConflictError as e:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!")
            oringinal_text = page.get(force = True, get_redirect = True)
        except pywikibot.exceptions.LockedPageError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the page is protected!")
            break
        except pywikibot.exceptions.AbuseFilterDisallowedError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!")
            break
        except pywikibot.exceptions.SpamblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!")
            break
        except pywikibot.exceptions.TitleblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!")
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error below:\n{e}\nThe edit is '{text[:100]}', and the summary is '{summary}'.")
    return False

def check_switch(site, switch_page_name:str) -> bool:
    switch_page = pywikibot.Page(site, switch_page_name)
    return json.loads(switch_page.text)["Automatically add authority control template"]["Enable"]

def has_authority_control(page, AUTHORITY_CONTROL_ID:tuple) -> bool:
    try:
        item = pywikibot.ItemPage.fromPage(page)
        repo = item.repo
        claims = item.get().get("claims", {})
        for prop_id in claims:
            if  int(prop_id[1:]) in AUTHORITY_CONTROL_ID:
                return True
    except pywikibot.exceptions.NoPageError:
        pass
    return False

def add_authority_control_template(page):
    text_list = page.text.split("\n")[::-1]
    place = 0
    for i in range(len(text_list)):
        if re.findall(r"(?:\{\{DEFAULTSORT:|\[\[(?:[Cc]at|[Cc]atgory):.*?\]\]|\{\{[Ss]tub|\{\{.*?-stub|\{\{.*?小作品|\{\{小條目)", text_list[i+1].replace(" ", "")):
          place = i+2
    text_list.insert(place, "{{Authority control}}")
    text = "\n".join(text_list[::-1])
    save(site, page, text, "根據維基數據資料添加[[Template:Authority control|權威控制模板]]")

def need_authority_control_template(page, AUTHORITY_CONTROL_ID:tuple) -> bool:
    if page.isRedirectPage():
        return False
    text = page.text
    for i in ("{{Authority control", "{{authority control", "{{規範控制", "{{规范控制", "{{權威控制", "{{权威控制"):
        if i in text:
            return False
    return has_authority_control(page, AUTHORITY_CONTROL_ID)

if __name__ == "__main__":
    site = pywikibot.Site("wikipedia:zh")
    log_json = pywikibot.Page(site, "User:Twelephant-bot/task/2/log.json")
    viewed_json = pywikibot.Page(site, "User:Twelephant-bot/task/2/viewed.json")
    try:
        viewed = json.loads(viewed_json.text)
        log = json.loads(log_json.text)
        assert isinstance(viewed, list) and isinstance(log, list)
        viewed = set(viewed)
    except:
        viewed = set()
        log = []
    for page in pagegenerators.AllpagesPageGenerator(site = site, filterredir = False):
        title = page.title()
        if title in viewed:
            continue
        if need_authority_control_template(page, AUTHORITY_CONTROL_ID):
            add_authority_control_template(page)
            log.append(title)
            save(site, log_json, json.dumps(log), "Update log")
            if not check_switch(site, "User:Twelephant-bot/setting.json"):
                break
        viewed.add(title)
        if len(viewed) % 50 == 0:
            save(site, viewed_json, json.dumps(list(viewed)), "Update log")
            if not check_switch(site, "User:Twelephant-bot/setting.json"):
                break
