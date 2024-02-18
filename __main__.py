import json
import time
from pprint import pformat
from typing import Any
import sys

from datetime import datetime

from urllib3 import PoolManager

from constants import CONFIG_FILE, TENDERS_FILE, WATCH_LIST
from snif_mice import Tender, get_opening_tender, get_warranty
from str_metric.html_template import GLOBAL_STYLE
from str_metric.levenshtein import html_output
import textwrap

http = PoolManager()

LOG_FILE = "watch.log"


def basic_str(obj):
    if isinstance(obj, str):
        return obj
    if isinstance(obj, int):
        return f"{obj:,}"
    if isinstance(obj, float):
        return f"{obj:,.3f}"
    assert False, f"`basic_str` only works on ints, floats, and strings, found type {type(obj)}, {obj = }"


def display_obj(obj: list | dict[str, Any] | str | int | float) -> str:
    """Turn into html"""
    if type(obj) in (str, int, float):
        return basic_str(obj)
    if isinstance(obj, list):
        res = "<ul>"
        for elem in obj:
            res += f"<li>{display_obj(elem)}</li>"
        return res + "</ul>"
    res = "<dl>"
    for k, v in obj.items():  # type: ignore
        res += f"<dt>{display_obj(k)}</dt><dd>{display_obj(v)}</dd>"
    return res + "</dl>"


def remove_obj(obj):
    if type(obj) in (str, int, float):
        return f'<span class="_removed">{obj}</span>'
    elif isinstance(obj, list):
        return list(map(lambda e: remove_obj(e), obj))
    elif isinstance(obj, dict):
        return {remove_obj(k): remove_obj(v) for k, v in obj.items()}
    assert False, f"don't know how to remove object of type {type(obj)}: {obj}"


def add_obj(obj):
    if type(obj) in (str, int, float):
        return f'<span class="_added">{obj}</span>'
    elif isinstance(obj, list):
        return list(map(lambda e: add_obj(e), obj))
    elif isinstance(obj, dict):
        return {add_obj(k): add_obj(v) for k, v in obj.items()}
    assert False, f"don't know how to add object of type {type(obj)}: {obj}"


def list_difference(old_list, new_list):
    _old_list = []
    _new_list = []

    for e in old_list:
        if e not in new_list:
            _old_list.append(remove_obj(e))
        else:
            _old_list.append(e)

    for e in new_list:
        if e not in old_list:
            _new_list.append(add_obj(e))
        else:
            _new_list.append(e)

    return _old_list, _new_list


def dict_difference(old_tender, new_tender):
    if isinstance(new_tender, str):
        return remove_obj(old_tender), new_tender

    _old_tender = {}
    _new_tender = {}

    for k in old_tender:
        if k not in new_tender:
            _old_tender[remove_obj(k)] = remove_obj(old_tender[k])
        elif isinstance(old_tender[k], list):
            old_list, new_list = list_difference(old_tender[k], new_tender[k])
            _old_tender[k] = old_list
            _new_tender[k] = new_list
        elif isinstance(old_tender[k], dict):
            _old_highlighted, _new_highlighted = dict_difference(
                old_tender[k], new_tender[k]
            )
            _old_tender[k] = _old_highlighted
            _new_tender[k] = _new_highlighted
        elif type(old_tender[k]) in (str, int, float):
            old = basic_str(old_tender[k])
            new = basic_str(new_tender[k])
            _old_highlighted, _new_highlighted = html_output(old, new)
            _old_tender[k] = _old_highlighted
            _new_tender[k] = _new_highlighted

    for k in new_tender:
        if k not in old_tender:
            _new_tender[add_obj(k)] = add_obj(new_tender[k])
    return _old_tender, _new_tender


def populate_reference():
    with open(TENDERS_FILE, "r+", encoding="utf-8") as file:
        tenders = json.load(file)
    with open(WATCH_LIST, "r+", encoding="utf-8") as file:
        target_list = json.load(file)

    if opening_tenders := target_list.get("opening_tenders"):
        for ministry_code in opening_tenders:
            if opening_ministry := tenders["opening_tenders"].get(ministry_code):
                opening_ministry = opening_ministry
            else:
                continue

            for tender_id in opening_tenders[ministry_code]:
                if old_tender := opening_ministry["tenders"].get(tender_id):
                    old_tender = old_tender
                else:
                    continue
                new_tender = get_opening_tender(ministry_code, tender_id) or {}

                if old_tender != new_tender:
                    log_change(old_tender, new_tender)
                    tenders["opening_tenders"][ministry_code]["tenders"][
                        tender_id
                    ] = new_tender

    with open(TENDERS_FILE, "w+", encoding="utf-8") as file:
        json.dump(tenders, file, ensure_ascii=False)


def notify_by_mail(
    old_tender: Tender,
    new_tender: Tender | str,
    ministry_name: str,
    tender_id: str,
    internal_id: str,
    mail_config,
):
    import smtplib
    import ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    sender_emails = mail_config["sender_email"]
    sender_email = sender_emails[0]["email"]
    sender_email = sender_emails[0]["email"]
    app_password = sender_emails[0]["password"]
    recievers = mail_config["notify_list"]

    tender_subject = old_tender["Tender Subject"]
    if len(tender_subject) > 120:
        tender_subject = tender_subject[:116] + " ..."
    else:
        tender_subject = tender_subject[:120]
    tender_subject.replace("\n", " ")

    message = MIMEMultipart("alternative")
    message["Subject"] = f"{tender_id} - {tender_subject}"
    message["From"] = sender_email
    message["To"] = ", ".join(recievers)

    _old_tender, _new_tender = dict_difference(old_tender, new_tender)

    _old_tender_display = display_obj(_old_tender)
    _new_tender_display = display_obj(_new_tender)

    text = textwrap.dedent(f"""\
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8">
                    <style> {GLOBAL_STYLE} </style>
                </head>
                <body>
                    <h1>{ministry_name} :: {tender_id}</h1>
                    <p>The Tender/Warranty of "{internal_id}" had changed</p>
                    <h2>From</h2>
                    <dl>
                        <dt>{tender_id}</dt>
                        <dd>
                            {_old_tender_display}
                        </dd>
                    </dl>
                    <h2>To</h2>
                    <dl>
                        <dt>{tender_id}</dt>
                        <dd>
                            {_new_tender_display}
                        </dd>
                    </dl>
                </body>
            </html>
            """)

    body_text = MIMEText(text, "html")
    message.attach(body_text)

    try:
        if ctx := ssl.create_default_context():
            server = smtplib.SMTP(mail_config["smtp_server"], mail_config["smtp_port"])
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recievers, message.as_string())
        else:
            print("FAILED TO ESTABLISH SSL CONTEXT")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        server.quit()  # type: ignore
        with open('.new.log', 'a') as file:
            file.write('\n')
            file.write(f"An email notification had been sent to [{', '.join(recievers)}]")
            file.write('\n')


def log_change(old, new):
    with open('.new.log', 'a') as file:
        file.write('\n')
        file.write('OLD:')
        file.write(textwrap.indent(pformat(old), '\t'))
        file.write('\n')
        file.write('NEW:')
        file.write(textwrap.indent(pformat(new), '\t'))
        file.write('\n')


def run_server():
    while True:
        with open('.new.log', 'a') as file:
            file.write(f"[{datetime.now()}]: Starting Checks \n")

        with open(TENDERS_FILE, "r+", encoding="utf-8") as file:
            tenders = json.load(file)
        with open(WATCH_LIST, "r+", encoding="utf-8") as file:
            target_list = json.load(file)
        with open(CONFIG_FILE, "r+", encoding="utf-8") as file:
            global_config = json.load(file)

        mail_config = global_config["mail_config"]
        change = False

        if opening_tenders := target_list.get("opening_tenders"):
            opening_tenders = opening_tenders
        else:
            continue

        if opening_tenders := target_list.get("opening_tenders"):
            for ministry_code in opening_tenders:
                if opening_ministry := tenders["opening_tenders"].get(ministry_code):
                    opening_ministry = opening_ministry
                else:
                    continue

                for tender_id in opening_tenders[ministry_code]:
                    if old_tender := opening_ministry["tenders"].get(tender_id):
                        old_tender = old_tender
                    else:
                        continue
                    new_tender = get_opening_tender(ministry_code, tender_id)
                    if new_tender != old_tender:
                        change = True
                        if internal_id := opening_tenders[ministry_code][tender_id]:
                            internal_id = ", ".join(
                                internal_id
                                if isinstance(internal_id, list)
                                else [internal_id]
                            )
                        log_change(old_tender, new_tender)
                        tenders["opening_tenders"][ministry_code]["tenders"][
                            tender_id
                        ] = new_tender

                        ministry_name = tenders["opening_tenders"][ministry_code][
                            "name"
                        ]

                        if not new_tender:
                            new_tender = f"The tender {ministry_name}::{tender_id} no longer exists as of {datetime.now()}"

                        notify_by_mail(
                            old_tender,
                            new_tender[0]
                            if isinstance(new_tender, list)
                            else new_tender,  # type: ignore
                            ministry_name,
                            tender_id,
                            internal_id,
                            mail_config,
                        )
                        tenders["opening_tenders"][ministry_code]["tenders"][
                            tender_id
                        ] = new_tender
        else:
            pass
        if warranties := target_list.get("warranties"):
            for ministry_code in warranties:
                if warranty_ministry := tenders["warranties"].get(ministry_code):
                    for tender_id in warranties[ministry_code]:
                        if old_tender := warranty_ministry["tenders"].get(tender_id):
                            new_tender = get_warranty(ministry_code, tender_id)
                            if new_tender != old_tender:
                                change = True
                                if internal_id := warranties[ministry_code][tender_id]:
                                    internal_id = ", ".join(
                                        internal_id
                                        if isinstance(internal_id, list)
                                        else [internal_id]
                                    )
                                log_change(old_tender, new_tender)
                                ministry_name = tenders["warranties"][ministry_code][
                                    "name"
                                ]

                                if not new_tender:
                                    new_tender = f"The tender {ministry_name}::{tender_id} no longer exists as of {datetime.now()}"

                                notify_by_mail(
                                    old_tender,
                                    new_tender,
                                    ministry_name,
                                    tender_id,
                                    internal_id,
                                    mail_config,
                                )
                                tenders["warranties"][ministry_code]["tenders"][
                                    tender_id
                                ] = new_tender
                        else:
                            continue
                else:
                    continue
        else:
            pass

        if change:
            with open(TENDERS_FILE, "w+", encoding="utf-8") as file:
                json.dump(tenders, file, ensure_ascii=False)
        with open('.new.log', 'a') as file:
            file.write(f'[{datetime.now()}]: Cycle finished \n')
        change = False
        time.sleep(60 * 60)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        if args[0] == 'refresh':
            populate_reference()
        elif args[0] == 'only':
            populate_reference()
            sys.exit(0)

    run_server()
