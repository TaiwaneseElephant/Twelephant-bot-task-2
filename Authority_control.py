# -*- coding: utf-8 -*-
import pywikibot
from pywikibot import pagegenerators, textlib
import json
import re
import os
import os.path
import datetime
import time

AUTHORITY_CONTROL_ID = {
  268, 214, 7859, 3372, 6804, 1907, 4186, 2092, 1908, 1707, 6829, 2349, 6792, 227, 1960, 347, 1248, 244, 1225, 2041, 409, 2750, 650, 350, 781, \
  3430, 3544, 1315, 245, 1986, 7902, 651, 791, 7303, 3563, 4055, 3223, 4423, 3723, 3993, 3562, 2980, 4038, 3920, 4143, 3863, 3601, 902, 886, \
  3065, 1362, 691, 1890, 950, 9984, 3348, 1375, 8189, 1736, 396, 8034, 349, 271, 5034, 1368, 1006, 1695, 7293, 1003, \
  947, 906, 5587, 7314, 1048, 2558
}

BOTTOM_PATTERN = re.compile(r"\{\{\s*(?:(?:[Tt](?:emplate)?|模板)\s*:)?\s*(?:DEFAULTSORT:.*?|[Ss]tub(?:\|.*?)?|.*?-stub(?:\|.*?)?|.*?小作品(?:\|.*?)?|小條目(?:\|.*?)?)\s*\}\}", flags = re.DOTALL)

def save(site, page, text:str, summary:str = "", minor:bool = True, max_retry_times:int = 3):
    e = None
    oringinal_text = ""
    if page.exists():
        oringinal_text = page.get(force = True, get_redirect = True)
    else:
      return False
    for _ in range(max_retry_times):
        try:
            if text == oringinal_text:
              return False
            page.text = text
            page.save(summary, minor = minor, bot=True)
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

def check_switch(site) -> bool:
    try:
        switch_page = pywikibot.Page(site, "User:Twelephant-bot/task/2/config.json")
        return json.loads(switch_page.text)["Enable"]
    except:
        return False

def has_authority_control(page) -> bool:
    try:
        item = pywikibot.ItemPage.fromPage(page)
        repo = item.repo
        claims = item.get().get("claims", {})
        for prop_id in claims:
            try:
                if  int(prop_id[1:]) in AUTHORITY_CONTROL_ID:
                    return True
            except:
                pass
    except pywikibot.exceptions.NoPageError:
        pass
    return False

def add_authority_control_template(site, page) -> None:
    text = page.get(force = True)
    cats = textlib.getCategoryLinks(text, site)
    text = textlib.removeCategoryLinks(text, site)
    match = BOTTOM_PATTERN.findall(text)
    text = BOTTOM_PATTERN.sub("", text)
    text = f"{text.rstrip()}\n{{{{Authority control}}}}\n{'\n'.join(match)}"
    text = textlib.replaceCategoryLinks(text, cats, site, add_only = True)
    return save(site, page, text, "根據維基數據資料添加[[Template:Authority control|權威控制模板]]")

def need_authority_control_template(page) -> bool:
    if page.isRedirectPage() or page.isDisambig():
        return False
    for template in page.itertemplates(namespaces=10):
      if template.title() == AUTHORITY_CONTROL_TEMPLATE:
          return False
    return has_authority_control(page)

def main(limit:int = float("inf")):
    global AUTHORITY_CONTROL_ID, AUTHORITY_CONTROL_TEMPLATE
    site = pywikibot.Site("wikipedia:zh")
    try:
      config = json.loads(pywikibot.Page(site, "User:Twelephant-bot/task/2/config.json").text)
      AUTHORITY_CONTROL_ID = config["authority control id"]
      AUTHORITY_CONTROL_TEMPLATE = config["template"]
      if not config["Enable"]:
        return
    except:
      print("Failed to load config")
      return
    log = []
    if os.path.exists("task-2-viewed.json"):
        try:
            with open("task-2-viewed.json", "r", encoding = "utf-8") as f:
                temp = json.load(f)
            assert isinstance(temp, dict)
            all_viewed = {}
            viewed = set()
            for i in temp:
                try:
                    if datetime.datetime.now(datetime.UTC) - datetime.datetime.strptime(i, "%Y-%m-%d").replace(tzinfo=timezone.utc) < datetime.timedelta(days = 30):
                        all_viewed[i] = temp[i]
                        viewed.update(temp[i])
                except Exception as e:
                    print(f"Failed to update all_viewed set, title: {temp[i]}, error:{e}")
            del temp
            try:
                with open("task-2-viewed-temp.json", "w", encoding = "utf-8") as f:
                    json.dump(all_viewed, f, ensure_ascii = False)
                os.replace("task-2-viewed-temp.json", "task-2-viewed.json")
            except Exception as e:
                print(f"Failed to update task-2-viewed.json, content:\n{all_viewed}, error:{e}")
        except:
            all_viewed = {}
            viewed = set()
    else:
        all_viewed = {}
        viewed = set()
    new_viewed = []
    for page in pagegenerators.AllpagesPageGenerator(site = site, namespace = 0, filterredir = False):
        title = page.title()
        if title in viewed:
            continue
        if need_authority_control_template(page) and page.botMayEdit():
            success = add_authority_control_template(site, page)
            if not success:
              continue
            log.append(title)
            if len(log) >= limit:
                break
            if not check_switch(site):
                break
        viewed.add(title)
        new_viewed.append(title)
        if len(new_viewed) == 50:
            time_now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
            if time_now in all_viewed:
                all_viewed[time_now].extend(new_viewed)
            else:
                all_viewed[time_now] = new_viewed
            with open("task-2-viewed-temp.json", "w", encoding = "utf-8") as f:
                json.dump(all_viewed, f, ensure_ascii = False)
            new_viewed = []
            os.replace("task-2-viewed-temp.json", "task-2-viewed.json")
            if not check_switch(site):
                break
        time.sleep(10)

if __name__ == "__main__":
    main()
