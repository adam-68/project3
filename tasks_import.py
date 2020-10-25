import win32clipboard
import json


def convert_to_dict():

    win32clipboard.OpenClipboard()
    tasks = win32clipboard.GetClipboardData().split("\r\n")
    win32clipboard.CloseClipboard()
    tasks_json = []

    for i in range(len(tasks)):
        row = tasks[i].split("\t")
        task = {
            "id": f"{i+1}".strip(),
            "name": row[0].strip().lower(),
            "webhook_url": row[1].strip(),
            "bypass": row[2].strip().lower()
        }
        tasks_json.append(task)

    with open("USER_INPUT_DATA/tasks.json", "w") as file:
        json.dump(tasks_json, file)


convert_to_dict()

