import datetime
import requests
import json
import sys
import os
import configparser
import smtplib
from jinja2 import Environment, FileSystemLoader
from email.message import EmailMessage

#
# Parses the config file $HOME/.trello-tracker.ini or ./.trello-tracker.ini
#
def parse_config():
    global config
    config = configparser.ConfigParser(allow_no_value=True)
    config_file = os.getenv("HOME") + "/.trello-tracker.ini"
    if not os.path.exists(config_file):
        config_file = "./.trello-tracker.ini"
    if not os.path.exists(config_file):
        raise Exception("Configuration file not found")
    config.read(config_file)


#
# Log a message with an auto-incrementing step number
#
def step_log(msg: str):
    global step
    print("%-2d - %s" % (step, msg))
    step += 1


#
# Log a substep (just append a tab to indent the log msg)
#
def substep_log(msg: str):
    print("     * %s" % msg)


#
# Prints the error message and exits with rc 1.
#
def step_error(msg: str):
    global step
    print("     ERROR: %s" % msg)
    sys.exit(1)


#
# Loads the lists defined in the ini file from your trello board,
# next reads all cards and their related checklists (if any).
#
def load_trello_lists():
    global trello_lists

    # Retrieving lists
    step_log("Retrieving lists from Trello Board")
    response = requests.get(URL_LISTS)
    if not response.ok:
        step_error("Unable to retreive list names")

    # populating map with list ids
    jsonResp = response.json()
    for l in jsonResp['lists']:
        list_name = l['name']
        list_id = l['id']
        if list_name in lists:
            newlist = {"name": list_name, "id": list_id, "cards": []}
            trello_dict[list_name] = newlist

    # Validate all trello_lists have been found
    for list_name in lists:
        if list_name not in trello_dict:
            step_error("Unable to identify list: %s" % list_name)
        trello_lists.append(trello_dict[list_name])

    # Loading cards now
    load_cards()


#
# Loads cards from all parsed lists
#
def load_cards():
    # Retrieving cards for each list
    for tl in trello_lists:
        step_log("Loading cards for list: %s" % tl['name'])
        url = URL_CARDS % (URL_BASE, tl['id'], apikey, token)
        response = requests.get(url)
        if not response.ok:
            step_error("Error retrieving cards from list: %s" % tl['name'])

        # iterating through cards
        jsonResp = response.json()
        for card in jsonResp:
            ignore_card = False
            for label in card['labels']:
                if label['name'] in ignore_labels:
                    ignore_card = True
                    break
            # ignoring card based on label
            if ignore_card:
                continue

            # Adding cards with done and pending checklist items
            tlc={"name": card["name"], "id": card["id"], "checklists": []}
            tl['cards'].append(tlc)

            # Retrieving checklists
            load_cards_checklists(tlc, card)


#
# Loads the checklists for given card
#
def load_cards_checklists(tlc: dict, card: dict):
    if not card['idChecklists']:
        return

    # Retrieving checklists for card
    substep_log("Loading cards checklist for card: %s" % card['name'])
    response = requests.get(URL_CHECKLISTS % (URL_BASE, card['id'], apikey, token))
    if not response.ok:
        step_error("Error retrieving checklists for card: %s" % card['name'])

    # Iterating through checklists
    for cl in response.json():
        cli = {"name": cl['name'], "id": cl['id'],
               "complete": [i['name'] for i in cl['checkItems'] if i['state'] == 'complete'],
               "incomplete": [i['name'] for i in cl['checkItems'] if i['state'] == 'incomplete']}
        tlc['checklists'].append(cli)


#
# Sending email
#
def send_email(body: str):
    if not mail_send:
        step_log("Email notification is disabled")
        dump_email_content(body)
        return

    step_log("Dumping email body")
    dump_email_content(body)

    if mail_ask_before_send:
        step_log("Ask before send email enabled")
        answer = input("     Send email (y/n): ").lower().strip()
        print("")

        while not(answer == "y" or answer == "yes" or
                  answer == "n" or answer == "no"):
            answer = input("Send email (y/n): ").lower().strip()

        if answer[0] == "n":
            return

    step_log("Sending email\n\tTo: %s\tSubject: %s" % (mail_to, mail_subject))
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = mail_subject
    msg['From'] = mail_from
    msg['To'] = mail_to

    # Send the message via defined smtp server
    s = smtplib.SMTP(mail_server)
    s.send_message(msg)
    s.quit()
    substep_log("Email sent")


#
# Simply dumps the email body
#
def dump_email_content(body: str):
    # Dumping output
    print()
    print("--------- Email Content --------")
    print()
    print(body)
    print()


# Parsing config
step = 1
parse_config()

# Trello config
apikey = config.get('trello', 'apikey')
token = config.get('trello', 'token')
boardid = config.get('trello', 'boardid')

#
# Loading variables for templating list names
#
now = datetime.datetime.now()
nowiso = now.isocalendar()
year = nowiso[0]
week = nowiso[1]
lists_dict = {"WEEK": week, "YEAR": year}

#
# Loading filters
#
lists = [l.format(**lists_dict) for l in config['filters']['lists'].split(",")]
ignore_labels = [k for k in config['filters']['ignorelabels'].split(",")]
donelabel = config['filters']['donelist'].format(**lists_dict)

#
# Email config
#
mail_from = config.get('email', 'from')
mail_to = config.get('email', 'to')
mail_server = config.get('email', 'server')
mail_subject = config.get('email', 'subject').format(**lists_dict)
mail_send = config.get('email', 'send').lower() in ['true', 'yes', '1']
mail_ask_before_send = config.get('email', 'ask_before_send').lower() in ['true', 'false', '1']

# Trello URLs
URL_BASE="https://api.trello.com"
URL_LISTS="%s/1/boards/%s?key=%s&token=%s&fields=name&lists=all" % (URL_BASE, boardid, apikey, token)
URL_CARDS="%s/1/lists/%s/cards?key=%s&token=%s"
URL_CHECKLISTS="%s/1/cards/%s/checklists?key=%s&token=%s"

# trello_lists content
# { "name": "List name", "id": "listid", cards: []}
# card definition
# { "name": "Card name", "id": "cardid", checklists: []}
# checklist definition
# { "name": "Checklist name", "id": "checklistid", complete: [], incomplete: []}
# note: complete and incomplete are string lists
trello_lists=[]
trello_dict={}

#
# Main workflow
#

# Retrieving pre-defined set of trello lists
load_trello_lists()

# content = open('/tmp/sample.json', 'r').read()
# trello_lists = json.loads(content)

# Dumping JSON object
# print(json.dumps(trello_lists))

# Loading the template
file_loader = FileSystemLoader('.')
env = Environment(loader=file_loader)
template = env.get_template('weekly.j2')
output = template.render(lists=trello_lists, week=week, donelabel=donelabel)

# Sending email
send_email(output)
