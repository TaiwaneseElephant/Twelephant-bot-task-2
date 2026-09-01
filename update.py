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
      query_limit = config["query limit"]
      if not config["Enable"]:
        return
    except:
      print("Failed to load config.")
      return
    properties = (" ".join(["wdt:P%d" % i for i in AUTHORITY_CONTROL_ID]))
    SparqlQuery = sparql.SparqlQuery()
    offset = 0
    pages = set()
    while True:
      result = SparqlQuery.query(query=query_string % (properties, query_limit, offset))
      if not result:
          break
      pages = pages or set(result)
      offset += limit
      time.sleep(6)
    pages = list(pages - set([page.title() for page in pwb.Page(site, template).embeddedin(namespaces =0)]))
    with open("pages_need_authority_control_template.json", "w") as f:
        json.dump(pages, f, ensure_ascii=False, indent=4))
    time.sleep(2592000)

main()
