# -*- coding: utf-8 -*-
import pywikibot as pwb
from pywikibot import pagegenerators, textlib
from pywikibot.data import sparql
import re
import time
import json

BOTTOM_PATTERN = re.compile(r"\{\{\s*(?:(?:[Tt](?:emplate)?|模板)\s*:)?\s*(?:DEFAULTSORT:.*?|[Ss]tub(?:\|.*?)?|.*?-stub(?:\|.*?)?|.*?小作品(?:\|.*?)?|小條目(?:\|.*?)?)\s*\}\}", flags = re.DOTALL)

def save(site, page, func = lambda x:x, summary:str = "", max_retry_times:int = 3):
    e = None
    if page.exists():
        oringinal_text = page.get(force = True, get_redirect = False)
    else:
      return False
    for _ in range(max_retry_times):
        try:
            page.text = func(oringinal_text, site)
            page.save(summary, minor = True, bot=True)
            return True
        except pwb.exceptions.EditConflictError as e:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!", flush=True)
            oringinal_text = page.get(force = True, get_redirect = True)
        except pwb.exceptions.LockedPageError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the page is protected!", flush=True)
            break
        except pwb.exceptions.AbuseFilterDisallowedError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!", flush=True)
            break
        except pwb.exceptions.SpamblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!", flush=True)
            break
        except pwb.exceptions.TitleblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!", flush=True)
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error below:\n{e}.", flush=True)
    return False

def check_switch(site) -> bool:
    try:
        switch_page = pwb.Page(site, "User:Twelephant-bot/task/2/config.json")
        return json.loads(switch_page.text)["Enable"]
    except:
        return False

def add_authority_control_template(text, site) -> None:
    cats = textlib.getCategoryLinks(text, site)
    text = textlib.removeCategoryLinks(text, site)
    match = BOTTOM_PATTERN.findall(text)
    text = BOTTOM_PATTERN.sub("", text)
    text = f"{text.rstrip()}\n{{{{Authority control}}}}\n{'\n'.join(match)}"
    text = textlib.replaceCategoryLinks(text, cats, site, add_only = True)
    return text

def hasTemplate(page, AUTHORITY_CONTROL_TEMPLATE) -> bool:
    for template in page.itertemplates(namespaces=10):
        if template.title() == AUTHORITY_CONTROL_TEMPLATE:
            return True
    return False

def getSparqlQuery(AUTHORITY_CONTROL_ID:list, query_string:str, query_limit:int) -> set:
    properties = (" ".join(["wdt:P%d" % i for i in AUTHORITY_CONTROL_ID]))
    SparqlQuery = sparql.SparqlQuery()
    offset = 0
    pages = set()
    while True:
        query = query_string % (properties, query_limit, offset)
        print(query)
        try:
            result = SparqlQuery.select(query)
        except Exception as e:
            print(f"SparqlQueryError: {e}", flush=True)
            time.sleep(60)
            continue
        result = [i["title"] for i in result]
        pages.update(result)
        print(len(result), flush=True)
        if len(result) < query_limit:
            break
        offset += query_limit
    return pages

def main(limit:int = float("inf")):
    site = pwb.Site("wikipedia:zh")
    try:
        config = json.loads(pwb.Page(site, "User:Twelephant-bot/task/2/config.json").text)
        AUTHORITY_CONTROL_ID = config["authority control id"]
        AUTHORITY_CONTROL_TEMPLATE = config["template"]
        query_string = config["query string"]
        query_limit = config["query limit"]
        summary = config["summary"]
        if not config["Enable"]:
            print("Stop!", flush=True)
            return
    except:
        print("Failed to load config.")
        return
    while True:
        try:
            pages_need_authority_control_template = getSparqlQuery(AUTHORITY_CONTROL_ID, query_string, query_limit)
            break
        except Exception as e:
            print(f"SparqlQueryError: {e}", flush=True)
            time.sleep(60)
    pages_need_authority_control_template = pages_need_authority_control_template
    print(len(pages_need_authority_control_template), flush=True)
    t = 0
    for title in pages_need_authority_control_template:
        page = pwb.Page(site, title)
        if not page.botMayEdit() or page.isRedirectPage() or page.isDisambig() or hasTemplate(page, AUTHORITY_CONTROL_TEMPLATE):
            continue
        success = save(site, page, add_authority_control_template, summary)
        if success:
            print(title)
            t += 1
            if  t >= limit:
                print("Finshed!", flush=True)
                break
            if t % 10 == 0 and not check_switch(site):
                print("Stop!", flush=True)
                break

if __name__ == "__main__":
    main(50)
