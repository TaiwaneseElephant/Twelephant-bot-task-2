# -*- coding: utf-8 -*-
import pywikibot as pwb
from pywikibot import pagegenerators, textlib
import re
import time

BOTTOM_PATTERN = re.compile(r"\{\{\s*(?:(?:[Tt](?:emplate)?|模板)\s*:)?\s*(?:DEFAULTSORT:.*?|[Ss]tub(?:\|.*?)?|.*?-stub(?:\|.*?)?|.*?小作品(?:\|.*?)?|小條目(?:\|.*?)?)\s*\}\}", flags = re.DOTALL)

def save(site, page, text:str, summary:str = "", minor:bool = True, max_retry_times:int = 3):
    e = None
    oringinal_text = ""
    if page.exists():
        oringinal_text = page.get(force = True, get_redirect = False)
    else:
      return False
    for _ in range(max_retry_times):
        try:
            if text == oringinal_text:
              return False
            page.text = text
            page.save(summary, minor = minor, bot=True)
            return True
        except pwb.exceptions.EditConflictError as e:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!")
            oringinal_text = page.get(force = True, get_redirect = True)
        except pwb.exceptions.LockedPageError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the page is protected!")
            break
        except pwb.exceptions.AbuseFilterDisallowedError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!")
            break
        except pwb.exceptions.SpamblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!")
            break
        except pwb.exceptions.TitleblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!")
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error below:\n{e}\nThe edit is '{text[:100]}', and the summary is '{summary}'.")
    return False

def check_switch(site) -> bool:
    try:
        switch_page = pwb.Page(site, "User:Twelephant-bot/task/2/config.json")
        return json.loads(switch_page.text)["Enable"]
    except:
        return False

def add_authority_control_template(site, page, summary) -> None:
    text = page.get(force = True)
    cats = textlib.getCategoryLinks(text, site)
    text = textlib.removeCategoryLinks(text, site)
    match = BOTTOM_PATTERN.findall(text)
    text = BOTTOM_PATTERN.sub("", text)
    text = f"{text.rstrip()}\n{{{{Authority control}}}}\n{'\n'.join(match)}"
    text = textlib.replaceCategoryLinks(text, cats, site, add_only = True)
    return save(site, page, text, summary, True)

def hasTemplate(page, AUTHORITY_CONTROL_TEMPLATE):
    for template in page.itertemplates(namespaces=10):
        if template.title() == AUTHORITY_CONTROL_TEMPLATE:
            return True
    return False

def getSparqlQuery(AUTHORITY_CONTROL_ID, query_string, query_limit) -> set:
    properties = (" ".join(["wdt:P%d" % i for i in AUTHORITY_CONTROL_ID]))
    SparqlQuery = sparql.SparqlQuery()
    offset = 0
    pages = set()
    while True:
        result = SparqlQuery.query(query=query_string % (properties, query_limit, offset))
        if not result:
            break
        pages = pages or set(result)
        offset += query_limit
        time.sleep(6)
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
            return
    except:
        print("Failed to load config.")
        return
    pages_have_template = set([page.title() for page in pwb.Page(site, AUTHORITY_CONTROL_TEMPLATE).embeddedin(namespaces=0)])
    pages_need_authority_control_template = getSparqlQuery(AUTHORITY_CONTROL_ID, query_string, query_limit) - pages_have_template
    for title in pages_need_authority_control_template:
        page = pwb.Page(site, title)
        if not page.botMayEdit() or page.isRedirectPage() or page.isDisambig() or hasTemplate(page, AUTHORITY_CONTROL_TEMPLATE):
              continue
        success = add_authority_control_template(site, page, summary)
        if success:
              print(title)
                if not check_switch(site):
                    break

if __name__ == "__main__":
    main()
