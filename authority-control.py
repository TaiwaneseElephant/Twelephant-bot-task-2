# -*- coding: utf-8 -*-
import pywikibot
from pywikibot import textlib
from pywikibot.data import sparql
import re, time, json, requests

DEFAULTSORT_PATTERN = re.compile(r"\{\{\s*DEFAULTSORT:[^}]+\s*\}\}")
STUB_PATTERN = re.compile(r"\{\{\s*(?:(?:[^|}]*?-)?[Ss]tub(?:\s*\|[^}]*?)?|[^|}]*?小作品(?:\s*\|[^}]*?)?|小條目(?:\s*\|[^}]*?)?)\s*\}\}")

def save(site, page, func = lambda x:x, summary:str = "", max_retry_times:int = 3, **kargs) -> bool:
    if page.exists() and page.botMayEdit():
        original_text = page.text
    else:
      return False
    for _ in range(max_retry_times):
        try:
            page.text = func(original_text, **kargs)
            if page.text != original_text:
                page.save(summary, minor = True, bot=True)
                return True
            else:
                print("No difference.")
                return False
        except pywikibot.exceptions.EditConflictError:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!", flush=True)
            original_text = page.get(force = True, get_redirect = False)
        except pywikibot.exceptions.LockedPageError:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the page is protected!", flush=True)
            break
        except pywikibot.exceptions.AbuseFilterDisallowedError:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!", flush=True)
            break
        except pywikibot.exceptions.SpamblacklistError:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!", flush=True)
            break
        except pywikibot.exceptions.TitleblacklistError:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!", flush=True)
            break
        except pywikibot.exceptions.OtherPageSaveError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed due to {e}!", flush=True)
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error.", flush=True)
    return False

def check_switch(site) -> bool:
    try:
        switch_page = pywikibot.Page(site, "User:Twelephant-bot/task/2/config.json")
        return json.loads(switch_page.text)["Enable"]
    except:
        return False

def add_authority_control_template(text, sitenow, template) -> str:
    cats = textlib.getCategoryLinks(text, sitenow)
    text = textlib.removeCategoryLinks(text, sitenow)
    DEFAULTSORT = DEFAULTSORT_PATTERN.findall(text)
    if DEFAULTSORT:
        DEFAULTSORT = f"\n{DEFAULTSORT[0]}"
    else:
        DEFAULTSORT = ""
    text = DEFAULTSORT_PATTERN.sub("", text)
    STUB = STUB_PATTERN.findall(text)
    text = STUB_PATTERN.sub("", text)
    text = f"{text.strip()}\n{{{{{template}}}}}{DEFAULTSORT}\n"
    text = textlib.replaceCategoryLinks(text, cats, sitenow, add_only = True)
    text = f"{text.strip()}\n{'\n'.join(STUB)}"
    return text

def getSparqlQuery(AUTHORITY_CONTROL_ID:list, query_string:str, query_limit:int) -> set:
    while True:
        try:
            SparqlQuery = sparql.SparqlQuery()
            break
        except Exception as e:
            print(f"SparqlQueryError: {e}", flush=True)
    pages = set()
    for id in AUTHORITY_CONTROL_ID:
        offset = 0
        while True:
            query = query_string % (id, query_limit, offset)
            print(query)
            tries = 0
            while tries < 30:
                try:
                    result = SparqlQuery.select(query)
                    if result is None:
                        raise Exception("'result' is 'None'.'")
                    break
                except Exception as e:
                    print(f"SparqlQueryError: {e}", flush=True)
                    time.sleep(10)
                    tries += 1
            if tries == 30:
                print("Skip due to exceeding max tries.")
                break
            result = [i["title"] for i in result]
            pages.update(result)
            print(len(result), flush=True)
            if len(result) < query_limit:
                break
            offset += query_limit
    return pages

def main() -> None:
    site = pywikibot.Site("wikipedia:zh")
    try:
        config = json.loads(pywikibot.Page(site, "User:Twelephant-bot/task/2/config.json").text)
        AUTHORITY_CONTROL_ID = config["authority control id"]
        template = config["template"]
        module = config["module"]
        query_string = config["query string"]
        query_limit = config["query limit"]
        summary = config["summary"]
        if not config["Enable"]:
            print("Stop!", flush=True)
            return
    except:
        print("Failed to load config.")
        return
    pages_need_authority_control_template = getSparqlQuery(AUTHORITY_CONTROL_ID, query_string, query_limit)
    print(len(pages_need_authority_control_template), flush=True)
    templatepage = pywikibot.Page(site, template, ns=10)
    modulepage = pywikibot.Page(site, module, ns=828)
    t = 0
    for title in pages_need_authority_control_template:
        page = pywikibot.Page(site, title)
        if page.isRedirectPage() or page.isDisambig() or any(tp in (templatepage, modulepage) for tp in page.itertemplates(namespaces=(10, 828))):
            continue
        success = save(site, page, add_authority_control_template, summary, sitenow = site, template = template)
        if success:
            print(title)
            t += 1
            if t % 10 == 0 and not check_switch(site):
                print("Stop!", flush=True)
                break

if __name__ == "__main__":
    main()
