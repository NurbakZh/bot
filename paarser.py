import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
}

def find_bitrix_session_id(script_tags):
    for script in script_tags:
        if script.string and "(window.BX||top.BX).message" in script.string:
            match = re.search(r"'bitrix_sessid':'(.*?)'", script.string)
            if match:
                bitrix_sessid = match.group(1)
                return bitrix_sessid
            else:
                continue
    return "no_bitrix"

def get_data_from_last_script(login, password, login_url, target_url, index_of_minimal_price):
    with requests.Session() as session:
        payload = {
            "tab": "main",
            "signature": "",  
            "signature_text_raw": "0JTQsNGC0LAg0LDQstGC0L7RgNC40LfQsNGG0LjQuCAyNy4xMC4yMDI0IDIwOjI5OjE0",
            "AUTH_FORM": "Y",
            "TYPE": "AUTH",
            "backurl": "/auth/?backurl=%2F",
            "USER_LOGIN": login,
            "USER_PASSWORD": password,
        }

        to_return = {"Минимальная цена": -1,
         "Пороговая цена для товара": -1}
        
        login_response = session.post(login_url, data=payload, headers=headers)
        if login_response.ok:
            
            soup = BeautifulSoup(login_response.text, "html.parser")
            b_tags = soup.find_all("b")
            nub = b_tags[len(b_tags) - 1].text.split('.')[0]
            nub1 = nub.replace(" ", "")
            nub2 = nub1.replace("\xa0", "")
            try:
                to_return["Пороговая цена для товара"] = int(nub2)
            except:
                to_return["Пороговая цена для товара"] = "Нет пороговой цены"

            data = {
                "cityId": 47597,
                "count": 1,
            }

            response = session.post(target_url, headers=headers, json=data)
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')

                a_tags = soup.find_all("a", attrs={"data-product-id": True}) 
                data_product_id = a_tags[0].get("data-product-id")

                script_tags = soup.find_all('script')
                bitrix_sessid = find_bitrix_session_id(script_tags)

                url = "https://omarket.kz/catalog/ajax_load_offers.php"
                payload_for_ajax = {
                    "PRODUCT_ID": data_product_id,
                    "bitrix_sessid": bitrix_sessid,
                    "FROM_CALC": "",
                    "SHOW_TRACE": "N",
                    "signature": "",
                    "signature_text_raw": "0JTQsNGC0LAg0LDQstGC0L7RgNC40LfQsNGG0LjQuCAyNy4xMC4yMDI0IDIwOjI5OjE0",
                    "USER_LOGIN": "Asyl12738@mail.ru",
                    "USER_PASSWORD": "Safa12738",
                }
                
                headers_ajax = {
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    "X-CSRF-Token": "eyJpdiI6Im5sM0RjTGxTK1Jpa25qQjB5anBNMlE9PSIsInZhbHVlIjoiTS8rMlJ1TGFidVVqSktuRlg0VnNlOTg2YTBjc2ZjTWhEWUkxd2RBaVNZbzR4NVBlNGo0K2MrMzVNT1pObTg5THovV1ZINnNBckcrbXd0U1VobHJYc0F5MEtSdlpTelBEQS9qWE9Pd0NtNWw4dEpuMGhLd0hIR2VhblRPU1BxazkiLCJtYWMiOiI1YjMzMzBjNGIwNzlmZmNmMTg4ZjBkOGE0ZmM5Mzk0MzhjMGMzZGFjNmUxMjBmYTcxYzkyODU2ZmQ3YzY1NTU1IiwidGFnIjoiIn0%3D",  # Replace with the actual CSRF token if needed
                    "X-Requested-With": "XMLHttpRequest",
                }

                response_ajax = session.post(url, headers=headers_ajax, data=payload_for_ajax)
                if response_ajax.ok:
                    soup = BeautifulSoup(response_ajax.text, 'html.parser')
                    price_divs = soup.find_all('div', class_='col-6')
                    prices = []
                    for i in range(len(price_divs)):
                        if (i % 10) == 3:
                            price_text = price_divs[i].get_text(strip=True)
                            price_text_new = price_text.replace(" ", "")
                            price_text_new2 = price_text_new.replace("\xa0", "")
                            prices.append(price_text_new2.replace("тг.", ""))
                    to_return["Минимальная цена"] = prices[index_of_minimal_price - 1]
                    return to_return
                else:
                    return f"УПС.... Не получается получить цены из-за ошибки: {response_ajax.status_code}. Напишите Нурбеку пожалуйста - @nurba_zh"
            else:
                return f"УПС.... Не получается получить информациб о товаре из-за ошибки: {response.status_code}. Напишите Нурбеку пожалуйста - @nurba_zh"
        else:
            return f"УПС.... Не получается зайти в ваш аккаунт из-за ошибки: {login_response.status_code}. Вы точно ввели правильные логин и пароль????? Если да, то напишите Нурбеку пожалуйста - @nurba_zh"

def change_price(login, password, login_url, price_new):
    with requests.Session() as session:
        id = login_url.split('?ID=')[1]
        payload = {
            "tab": "main",
            "signature": "",  
            "signature_text_raw": "0JTQsNGC0LAg0LDQstGC0L7RgNC40LfQsNGG0LjQuCAyNy4xMC4yMDI0IDIwOjI5OjE0",
            "AUTH_FORM": "Y",
            "TYPE": "AUTH",
            "backurl": "/auth/?backurl=%2F",
            "USER_LOGIN": login,
            "USER_PASSWORD": password,
        }

        login_response = session.post(login_url, data=payload, headers=headers)
        if login_response.ok:
            soup = BeautifulSoup(login_response.text, 'html.parser')
            script_tags = soup.find_all('script')
            input_tags = soup.find_all("input", {"name": re.compile(r"^pos\[")})

            poses = []
            prices = []    

            for input_elem in input_tags:
                input_id = input_elem.get('id')
                input_name = input_elem.get('name') 
                poses.append({input_name : "Y"})
                prices.append({f"price_no_nds{input_name.split('pos')[1].split('[P')[0]}" : price_new})
            bitrix_sessid = find_bitrix_session_id(script_tags)

            url = f'https://omarket.kz/personal/trade/moffers/save_form.php?ID={id}'

            payload_for_ajax = {
                "trade[DISCOUNT]": 0,
                "tradeOfferId": id,
                "save_form": "Y",
                "agreement-field": "Y",
                "price_no_nds_all": price_new,
                "bitrix_sessid": bitrix_sessid,
            }

            
            for pose in poses:
                payload_for_ajax.update(pose)

            for price in prices:
                payload_for_ajax.update(price)
            
            headers_ajax = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "X-CSRF-Token": "eyJpdiI6Im5sM0RjTGxTK1Jpa25qQjB5anBNMlE9PSIsInZhbHVlIjoiTS8rMlJ1TGFidVVqSktuRlg0VnNlOTg2YTBjc2ZjTWhEWUkxd2RBaVNZbzR4NVBlNGo0K2MrMzVNT1pObTg5THovV1ZINnNBckcrbXd0U1VobHJYc0F5MEtSdlpTelBEQS9qWE9Pd0NtNWw4dEpuMGhLd0hIR2VhblRPU1BxazkiLCJtYWMiOiI1YjMzMzBjNGIwNzlmZmNmMTg4ZjBkOGE0ZmM5Mzk0MzhjMGMzZGFjNmUxMjBmYTcxYzkyODU2ZmQ3YzY1NTU1IiwidGFnIjoiIn0%3D",  # Replace with the actual CSRF token if needed
                "X-Requested-With": "XMLHttpRequest",
            }

            response_change = session.post(url, data=payload_for_ajax, headers=headers_ajax)
            if response_change.ok:
                response_data = response_change.json()
                if response_data.get('status') == 'ok':
                    message = f"Success: {response_data.get('message')}"
                    # Handle success: reload or redirect based on response
                else:
                    message = f"Error: {response_data.get('message')}"
                    # Handle specific error types if needed
            else:
                message = "Failed to submit form. Server error."
            
            return message





def get_price(login, password, login_url, target_url, index):
    data = get_data_from_last_script(login, password, login_url, target_url, index)
    return int(data["Минимальная цена"])

if __name__ == '__main__':
    login_url = "https://omarket.kz/personal/trade/moffers/edit.php?ID=17856318"
    target_url = "https://omarket.kz/catalog/ecc_kancelyarskie_tovary/ecc_nastolnye_prinadlezhnosty/dyrokol/dyrokol3.html"

    get_price("Asyl12738@mail.ru", "Safa12738", login_url, target_url, 1)
    change_price("Asyl12738@mail.ru", "Safa12738", login_url, 990)