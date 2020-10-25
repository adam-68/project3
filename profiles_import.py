from urllib.parse import quote_plus
import json
import win32clipboard


def convert_to_dict():

    win32clipboard.OpenClipboard()
    profiles = win32clipboard.GetClipboardData().split("\r\n")
    win32clipboard.CloseClipboard()
    profiles_json = []

    for profile in profiles:
        row = profile.split("\t")
        try:
            curr_profile = {'first_name': row[0].strip(),
                            'last_name': row[1].strip(),
                            'email': quote_plus(row[2].strip()),
                            'phone': quote_plus(row[3].strip()),
                            'street': quote_plus(row[4].strip()),
                            'house_number': quote_plus(row[5].strip()),
                            'post_code': row[6].strip(),
                            'city': row[7].strip()}
            profiles_json.append(curr_profile)
        except Exception as error:
            print(f"Error with importing profiles: {error}")
            return

    with open("USER_INPUT_DATA/profiles.json", "w") as file:
        json.dump(profiles_json, file)


convert_to_dict()
