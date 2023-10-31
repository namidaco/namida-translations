import json


def main():
    with open("ru_RU.json", "r+", encoding="utf-8-sig") as file:
        json_data = json.load(file)

        for key in list(json_data.keys()):
            json_data[key] = json_data[key].replace('\'', "`").replace(',', '.').replace("\"", "`")

        for key in list(json_data.keys()):
            new_value = input(f"{json_data[key]}: ")

            if new_value == '':
                continue
            if new_value == "!cancel":
                break

            json_data[key] = new_value

    print(json_data)
    with open("ru_RU.json", "w+", encoding="utf-8-sig") as file:
        json_data = str(json_data)
        file.write(json_data.replace(",", ",\n").replace("\'", "\""))


if __name__ == "__main__":
    main()
