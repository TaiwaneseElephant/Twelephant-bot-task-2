from pywikibot.data import sparql
from pywikibot import pagegenerators
import pywikibot as pwb
import json
import time

def main():
    site = pwb.Site("wikipedia:zh")
    try:
      config = json.loads(pwb.Page(site, "User:Twelephant-bot/task/2/config.json").text)
      template = config["template"]
      AUTHORITY_CONTROL_ID = config["authority control id"]
      query_string = config["query string"]
      updatepage = config["updatepage"]
      updatesummary = config["updatesummary"]
      if not config["Enable"]:
        return
    except:
      print("Failed to load config.")
      return
    properties = (" ".join(["wdt:P%d" % i for i in AUTHORITY_CONTROL_ID]))
    SparqlQuery = sparql.SparqlQuery()
    result = SparqlQuery.query(query=query_string % properties)
    pages = set([page["title"] for page in result])- set([page.title() for page in pwb.Page(site, template).embeddedin(namespaces =0)])
    log_page = pwb.Page(site, updatepage)
    log_page.text = json.dumps(pages)
    log_page.save(minor=True, bot=True, summary=updatesummary)
    time.sleep(2592000)

main()
