import urllib

import requests
import lxml.html
import traceback
import rdflib
from rdflib import Literal, XSD
import sys

# --------------------------------------- Globals ---------------------------------------------
wiki_prefix = 'http://en.wikipedia.org/wiki/'
nations_url = 'https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)'
president_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/president')
prime_minister_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/prime_minister')
population_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/population')
area_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/area')
government_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/government')
capital_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/capital')
born_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/born')
type_relation = rdflib.URIRef(f'http://en.wikipedia.org/wiki/type')
ontology_graph = rdflib.Graph()


# return the elements from the given xpath query on the given url
def get_xpath_result(url, query):
    res = requests.get(url)
    doc = lxml.html.fromstring(res.content)
    return doc.xpath(query)


# builds country ontology based on the given url
def build_country_information(url):
    country_url = "http://en.wikipedia.org" + url
    info_box_query = "//table[contains(@class,'infobox')]"
    info_box = get_xpath_result(country_url, info_box_query)[0]
    country_name = get_xpath_result(country_url, "//h1[contains(@id,'firstHeading')]/text()")[0].replace(" ", "_")
    rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
    rdflib_country_fix = rdflib.URIRef(f'http://en.wikipedia.org/wiki/country')
    ontology_graph.add((rdflib_country, type_relation, rdflib_country_fix))

    # handle capital cities information
    capital_cities = get_capital_cities_information(info_box, country_name)
    set_capital_cities(capital_cities, country_name)

    # handle population information
    population = get_population_information(info_box, country_name)
    set_population(country_name, population)

    # handle area information
    area = get_area_information(info_box, country_name)
    set_area(country_name, area)

    # handle gonvernment informaiton
    government = get_government_information(info_box, country_name)
    set_government(government, country_name)

    # handle president information
    president = get_president_information(info_box, country_name)
    set_president_information(president, country_name)

    # handle prime minister information
    prime_ministers = get_prime_minister_information(info_box, country_name)
    set_pm_information(prime_ministers, country_name)


def get_capital_cities_information(info_box, country_name):
    capital_queries = [
        ".//th[contains(text(),'Capital')]/..//td[1]//a[not(contains(@title,'coordinate')) and contains(@title,text())]/text()",
        ".//th[contains(text(),'Capital')]/..//td[1]//a[not(contains(@title,'coordinate'))]/@title"]
    for q in capital_queries:
        capitals = info_box.xpath(q)
        if (len(capitals) > 0):
            break
    if (len(capitals) == 0):
        if (country_name == "Gibraltar"):
            capitals = ["Gibraltar"]
    return capitals


def get_population_information(info_box, country_name):
    population_queries = [".//tr//a[contains(text(),'Population')]/../..//following-sibling::tr[1]/td//text()",
                          ".//th[contains(text(),'Population')]/..//following-sibling::tr[1]//td//text()"]
    for q in population_queries:
        population = info_box.xpath(q)
        if (len(population) > 0):
            break
    if (len(population) != 0):
        population = extract_population(population)
        return population
    return None


# sets prime minister dob and prime minister it self
def set_pm_information(pm_urls, country_name):
    rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
    if (pm_urls == "None"):
        return
    if (len(pm_urls) > 1):
        for pm in pm_urls:
            pm_url = 'http://en.wikipedia.org' + pm
            pm_name = get_xpath_result(pm_url, "//h1[contains(@id,'firstHeading')]/text()")[0].replace(" ", "_")
            pm_bday = get_xpath_result(pm_url,
                                       "//table[contains(@class,'infobox')]//th[contains(text(),'Born')]/..//td[1]//span[contains(@class,'bday')]//text()")
            rdf_pm_name = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{pm_name}')
            if (len(pm_bday) != 0):
                rdf_dob = Literal(pm_bday[0], datatype=XSD.date)
                ontology_graph.add((rdf_pm_name, born_relation, rdf_dob))
            ontology_graph.add((rdflib_country, prime_minister_relation, rdf_pm_name))
    else:
        pm_url = 'http://en.wikipedia.org' + pm_urls[0]
        pm_name = get_xpath_result(pm_url, "//h1[contains(@id,'firstHeading')]/text()")[0].replace(" ", "_")
        pm_bday = get_xpath_result(pm_url,
                                   "//table[contains(@class,'infobox')]//th[contains(text(),'Born')]/..//td[1]//span[contains(@class,'bday')]//text()")
        rdf_pm_name = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{pm_name}')
        if (len(pm_bday) != 0):
            rdf_dob = Literal(pm_bday[0], datatype=XSD.date)
            ontology_graph.add((rdf_pm_name, born_relation, rdf_dob))
        ontology_graph.add((rdflib_country, prime_minister_relation, rdf_pm_name))


# get the prime minister information from the infobox of the country
def get_prime_minister_information(info_box, country_name):
    prime_minister_url_queries = [
        ".//tr//a[contains(text(),'Government')]/../..//following-sibling::tr//a[text()='Prime Minister']/../../..//td[1]//span//a[boolean(@title)]/@href",
        ".//th[contains(text(),'Government')]/../..//following-sibling::tr//a[text()='Prime Minister']/../../..//td[1]//span//a[boolean(@title)]/@href",
        ".//a[text() = 'Prime Minister']/../../..//td[1]//a[boolean(@title)]/@href",
        ".//th//a[contains(text(),'Government')]/../..//following-sibling::tr//a[contains(text(),'Prime minister')]/../../..//td[1]//a/@href"]
    for q in prime_minister_url_queries:
        vp_url = info_box.xpath(q)
        if (len(vp_url) > 0):
            break
    if (len(vp_url) == 0):
        vp_url = "None"
    return vp_url


# get the government information from the country info box
def get_government_information(info_box, country_name):
    government_queries = [".//tr//a[contains(text(),'Government')]/../..//td[1]//a[boolean(@title)]//text()",
                          ".//th[contains(text(),'Government')]/..//td[1]//a[boolean(@title)]//text()"]
    for q in government_queries:
        government = info_box.xpath(q)
        if (len(government) > 0):
            break
    if (len(government) == 0):
        return None
    result = ""
    for text in government:
        result += text + " "
    result = result.replace(" ", "_")
    result = result[0:-1]
    return result


# sets the gonverment relation to it's country
def set_government(government, country_name):
    if (government != None):
        rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
        rdflib_government = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{government}')
        ontology_graph.add((rdflib_country, government_relation, rdflib_government))


def get_president_information(info_box, country_name):
    president_url_queries = [
        ".//tr//a[contains(text(),'Government')]/../..//following-sibling::tr//a[text()='President']/../../..//td[1]//a[boolean(@title)]/@href",
        ".//th[contains(text(),'Government')]/../..//following-sibling::tr//a[text()='President']/../../..//td[1]//a[boolean(@title)]/@href"]
    for q in president_url_queries:
        president_url = info_box.xpath(q)
        if (len(president_url) > 0):
            break

    if (len(president_url) == 0):
        president_url = "None"
    if (country_name == "United_States" or country_name == "Trinidad_and_Tobago"):
        president_url = [president_url[0]]
    return president_url


def set_president_information(presidents_urls, country_name):
    rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
    if (presidents_urls == "None"):
        return
    if (len(presidents_urls) > 1):
        for president in presidents_urls:
            president_url = 'http://en.wikipedia.org' + president
            president_name = get_xpath_result(president_url, "//h1[contains(@id,'firstHeading')]/text()")[0].replace(
                " ", "_")
            president_bday = get_xpath_result(president_url,
                                              "//table[contains(@class,'infobox')]//th[contains(text(),'Born')]/..//td[1]//span[contains(@class,'bday')]//text()")
            rdf_p_name = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{president_name}')
            if (len(president_bday) != 0):
                rdf_dob = Literal(president_bday[0], datatype=XSD.date)
                ontology_graph.add((rdf_p_name, born_relation, rdf_dob))
            ontology_graph.add((rdflib_country, president_relation, rdf_p_name))
    else:
        president_url = 'http://en.wikipedia.org' + presidents_urls[0]
        president_name = get_xpath_result(president_url, "//h1[contains(@id,'firstHeading')]/text()")[0].replace(" ",
                                                                                                                 "_")
        president_bday = get_xpath_result(president_url,
                                          "//table[contains(@class,'infobox')]//th[contains(text(),'Born')]/..//td[1]//span[contains(@class,'bday')]//text()")
        rdf_p_name = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{president_name}')
        if (len(president_bday) != 0):
            rdf_dob = Literal(president_bday[0], datatype=XSD.date)
            ontology_graph.add((rdf_p_name, born_relation, rdf_dob))
        ontology_graph.add((rdflib_country, president_relation, rdf_p_name))


def get_area_information(info_box, country_name):
    area_queries = [".//tr//a[contains(text(),'Area')]/../..//following-sibling::tr[1]/td//text()",
                    "//th[contains(text(),'Area')]/..//following-sibling::tr[1]/td[1]//text()"]
    for q in area_queries:
        area = info_box.xpath(q)
        if (len(area) > 0):
            break
    area = extract_area(area[0], country_name)
    return area


# insert the capital cities the ontology graph
def set_capital_cities(list_capitals, country_name):
    rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
    if (len(list_capitals) == 0):
        rdflib_capital = rdflib.URIRef(f'http://en.wikipedia.org/wiki/None')
        ontology_graph.add((rdflib_country, capital_relation, rdflib_capital))
    else:
        for capital in list_capitals:
            rdflib_capital = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{capital.replace(" ", "_")}')
            ontology_graph.add((rdflib_country, capital_relation, rdflib_capital))


def set_area(country_name, area):
    if (area != None):
        rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
        rdflib_area = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{area}')
        ontology_graph.add((rdflib_country, area_relation, rdflib_area))


def extract_area(area, country_name):
    list = area.split()
    res = ""
    if (len(list) == 1):
        return list[0] + "_km2"
    else:
        i = 0
        while i < len(list):
            if (list[i].find('km') != -1):
                break
            i = i + 1
        res = list[i - 1] + "_km2"

    if (country_name == "American_Samoa" or country_name == "United_States"):
        res = res[1:]

    return res


def set_population(country_name, population):
    if (population != None):
        rdflib_country = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{country_name}')
        rdflib_population = rdflib.URIRef(f'http://en.wikipedia.org/wiki/{population}')
        ontology_graph.add((rdflib_country, population_relation, rdflib_population))


# extracts the population number from the population list which may contain characters which are not numbers
def extract_population(population):
    found = True
    for item in population:
        found = True
        item = item.split()
        for sub_item in item:
            found = True
            for char in sub_item:
                if (not char.isdigit() and char != ','):
                    found = False
                    break;
            if (found):
                return sub_item
    return None


# builds the ontology graph based on the list of united nations
def build_graph():
    query_country_tds = "//table[@id='main']//td[1]"
    sub_query1 = "..//span//a/@href"
    sub_query2 = "..//i[1]/a[1]/@href"
    list_of_tds = get_xpath_result(nations_url, query_country_tds)
    for country_td in list_of_tds:
        country_url = country_td.xpath(sub_query1)
        if (not country_url):
            country_url = country_td.xpath(sub_query2)
        if (len(country_url) != 0):
            build_country_information(country_url[0])


def ontology_main(ontology_name):
    build_graph()
    try:
        # ontology_graph.serialize('ontology.nt', format='nt')
        ontology_graph.serialize(ontology_name, format='nt')
    except:
        print('saving as rdf')
        ontology_graph.serialize('ontology.rdf', format='rdf')
    print('finish generating graph')


# ------------------------------------- NLP Section -----------------------------------------


def filter_answer_from_resp(resp, case_nine_flag=False):
    out = []
    rel = None
    for row in resp:
        try:
            ans = row[0].split(wiki_prefix, 1)[1]
            if case_nine_flag:
                rel = row[1].split(wiki_prefix, 1)[1]
        except:
            ans = row[0]
        ans = ans.replace('_', ' ')
        ans = urllib.parse.unquote(ans)
        out.append(ans)
    ans = ', '.join(out)
    return ans, rel


def query_first_option(g, query_text):
    try:
        resp = g.query(f"""
        select ?x
        where {{ {query_text} ?x .
        }}""")
        out = filter_answer_from_resp(resp)
        print(out[0])
    except Exception as e:
        print(f'Error: {e} - \nquery was in wrong format / ontology doesn\'t has the answer ')


def query_second_option(g, query_text):
    try:
        resp = g.query(f"""
        select ?x
        where {{ {query_text} ?y .
        ?y <{wiki_prefix}born> ?x .
        }}""")
        out = filter_answer_from_resp(resp)
        print(out[0])
    except Exception as e:
        print(f'Error: {e} - \nquery was in wrong format / ontology doesn\'t has the answer ')


def query_third_option(g, query_text):
    try:
        resp = g.query(f"""
        select ?x ?y
        where{{
        ?x ?y {query_text} .
        }}""")
        res, title = filter_answer_from_resp(resp, True)
        if len(title.split('_')) == 2:
            title = 'Prime minister'
        else:
            title = 'President'
        print(f'{title} of {res}')
    except Exception as e:
        print(f'Error: {e} - \nquery was in wrong format / ontology doesn\'t has the answer ')


def get_country(sfx_list):
    country = ' '.join(sfx_list).replace(' ', '_')
    return country


def extract_role(sfx):
    if str.lower(sfx[0]) == 'president':
        return 'president'
    elif str.lower(' '.join(sfx[:2])) == 'prime minister':
        return 'prime minister'
    else:
        return None


def process_qs_1_to_6(g, f_word, sfx):
    # qs pattern 1,2
    if f_word == 'who':
        if sfx[0] == 'president':
            country = get_country(sfx[2:])
            query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}president>"
        elif str.lower(' '.join(sfx[:2])) == 'prime minister':
            country = get_country(sfx[3:])
            query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}prime_minister>"
        else:
            sfx_qs = ' '.join(sfx)
            print(f'error in WHO question: {f_word} is the {sfx_qs}')
    else:
        # qs pattern 3,4,5,6
        if str.lower(sfx[0]) == 'population':
            country = get_country(sfx[2:])
            query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}population>"
        elif str.lower(sfx[0]) == 'area':
            country = get_country(sfx[2:])
            query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}area>"
        elif str.lower(sfx[0]) == 'government':
            country = get_country(sfx[2:])
            query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}government>"
        elif str.lower(sfx[0]) == 'capital':
            country = get_country(sfx[2:])
            query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}capital>"
        else:
            sfx_qs = ' '.join(sfx)
            raise (f"error in WHAT question: {f_word} is the {sfx_qs}")
    query_first_option(g, query_pat)


def process_qs_7_to_8(g, f_word, sfx):
    role = extract_role(sfx)
    if role == 'president':
        country = get_country(sfx[2:-1])
        query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}president>"
    elif role == 'prime minister':
        country = get_country(sfx[3:-1])
        query_pat = f"<{wiki_prefix}{country}> <{wiki_prefix}prime_minister>"
    else:
        sfx_qs = ' '.join(sfx)
        raise Exception(f'error in WHAT question: {f_word} is the {sfx_qs}')
    query_second_option(g, query_pat)


def process_question(qs):
    print('start processing questions:')
    print(qs)
    g = rdflib.Graph()
    g.parse('ontology.nt', format='nt')
    try:
        first_word = str.lower(qs.split(' ')[0])
        if first_word in ['who', 'what']:
            try:
                # pattern 9
                if str.lower(qs.split(' ')[2]) != 'the':
                    entity = '_'.join(qs[:-1].split(' ')[2:])
                    query_third_option(g, f'<{wiki_prefix}{entity}>')
                else:
                    suffix = qs[:-1].split(' ')[3:]
                    process_qs_1_to_6(g, first_word, suffix)
            except:
                print('Error: failed to retrieve the third word')
        elif first_word == 'when':
            suffix = qs[:-1].split(' ')[3:]
            process_qs_7_to_8(g, first_word, suffix)

    except:
        print('Error in processing question from user')


def main():
    if sys.argv[1] == "create":
        print("Creating Ontology Graph")
        ontology_main(sys.argv[2])
    elif sys.argv[1] == "question":
        qs = ' '.join(sys.argv[2:])
        process_question(qs)
    else:
        print("input is illegal, exiting...")


if __name__ == '__main__':
    main()
