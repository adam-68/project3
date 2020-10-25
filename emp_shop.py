from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from bs4 import BeautifulSoup
import json
import requests
import datetime
import time
import random
import re


class EmpShop:
    def __init__(self, curr_task, curr_profile):
        self.task = curr_task
        self.profile = curr_profile
        self.s = requests.Session()
        self.product_url = ""
        self.csrf_token = ""
        self.pid = ""
        self.checkout_data = ""
        self.address_data = ""
        self.webtrekkpid = ""
        self.error_num = 0
        queue = Interpreter()
        self.proxy = queue.get_proxy()
        self.queue = queue
        self.payment = ""
        if curr_task['bypass'] == "enabled":
            self.bypass = "waiting"
        else:
            self.bypass = "disabled"

    def wait_for_product(self):
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Service-Worker-Navigation-Preload": "true",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            if self.bypass == "waiting":
                print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] "
                      f"Looking for bypass product...")
                response = self.s.get("https://www.emp-shop.pl/fun-i-styl/dla-domu/funko-pop/funko-edycje-limitowane/"
                                      "?srule=release-date&start=0&sz=60", headers=headers, proxies=self.proxy, timeout=6)
                self.product_url = "https://www.emp-shop.pl/" + BeautifulSoup(response.text,
                                   "html.parser").find("a", {"class": "product-link thumb-link"})["href"]
            elif self.bypass == "configured" or self.bypass == "disabled":
                print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] "
                      f"Waiting for product...")
                response = self.s.get(f"https://www.emp-shop.pl/search?q=funko+{self.task['name']}", headers=headers,
                                      proxies=self.proxy, timeout=6)
                if "Dodaj do koszyka</span>" in response.text:
                    self.product_url = "https://www.emp-shop.pl" + \
                                       re.search(rf'/p/(.*?){self.task["name"]}(.*?)\.html', response.text).group()
                    self.csrf_token = re.search('csrf_token" value="(.*?)"', response.text).group().split('"')[-2]
                    self.pid = re.search('id="pid" value="(.*?)"', response.text).group().split('"')[-2]
                    self.webtrekkpid = re.search('id="webtrekkpid" value="(.*?)"', response.text).group().split('"')[-2]
                    self.cart_add()
                    return
                else:
                    curr_url = re.search(rf'/p/(.*?){self.task["name"]}(.*?)\.html', response.text)

                headers['Referer'] = f"https://www.emp-shop.pl/search?q=funko+{self.task['name']}"
                while not curr_url:
                    time.sleep(.1)
                    response = self.s.get(f"https://www.emp-shop.pl/search?q=funko+{self.task['name']}", headers=headers,
                                          proxies=self.proxy, timeout=6)
                    if "Dodaj do koszyka</span>" in response.text:
                        self.product_url = "https://www.emp-shop.pl" + \
                                           re.search(rf'/p/(.*?){self.task["name"]}(.*?)\.html', response.text).group()
                        self.csrf_token = re.search('csrf_token" value="(.*?)"', response.text).group().split('"')[-2]
                        self.pid = re.search('id="pid" value="(.*?)"', response.text).group().split('"')[-2]
                        self.webtrekkpid = \
                            re.search('id="webtrekkpid" value="(.*?)"', response.text).group().split('"')[-2]
                        self.cart_add()
                        return
                    else:
                        curr_url = re.search(rf'/p/(.*?){self.task["name"]}(.*?)\.html', response.text)

                self.product_url = "https://www.emp-shop.pl" + curr_url.group()
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Waiting for product: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.wait_for_product()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Waiting for product: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.wait_for_product()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Waiting for product: "
                  f"Timeout. Retrying...")
            self.wait_for_product()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Waiting for product: "
                  f"{error}. Retrying...")
            self.wait_for_product()
            return

        self.load_product_page()
        return

    def load_product_page(self):
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                          " (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                      "application/signed-exchange;v=b3;q=0.9",
            "Service-Worker-Navigation-Preload": "true",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Referer": "https://www.emp-shop.pl/fun-i-styl/dla-domu/funko-pop/funko-edycje-limitowane/?srule="
                       "release-date&start=0&sz=60",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] "
                  f"Loading product page...")
            response = self.s.get(self.product_url, headers=headers, proxies=self.proxy, timeout=5)
            while "Dodaj do koszyka</span>" not in response.text:
                time.sleep(.5)
                response = self.s.get(self.product_url, headers=headers, proxies=self.proxy, timeout=5)
            self.csrf_token = re.search('csrf_token" value="(.*?)"', response.text).group().split('"')[-2]
            self.pid = re.search('id="pid" value="(.*?)"', response.text).group().split('"')[-2]
            self.webtrekkpid = re.search('id="webtrekkpid" value="(.*?)"', response.text).group().split('"')[-2]
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Product page: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_product_page()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Product page: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_product_page()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Product page: "
                  f"Timeout. Retrying...")
            self.load_product_page()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Product page: "
                  f"{error}. Retrying...")
            self.load_product_page()
            return

        self.cart_add()
        return

    def cart_add(self):
        data = f"uuid=&source=&Quantity=1.0&cartAction=update&" \
               f"csrf_token={self.csrf_token.replace('=', '%3D')}&pid={self.pid}&webtrekkpid={self.webtrekkpid}"
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/83.0.4103.116 Safari/537.36",
            "Content-Length": str(len(data)),
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "ADRUM": "isAjax:true",
            "Service-Worker-Navigation-Preload": "true",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": self.product_url,
            "Origin": "https://www.emp-shop.pl",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Adding to cart...")
            response = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/Cart-AddProduct?"
                                   "format=ajax", headers=headers, data=data, proxies=self.proxy,
                                   timeout=5)
            while "Artykuł został dodany do koszyka." not in response.text:
                self.error_num += 1
                if self.error_num > 10:
                    print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Carting error."
                          f" Retrying... ")
                    self.error_num = 0
                    self.load_product_page()
                    return
                time.sleep(.1)
                response = self.s.post(
                    "https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/Cart-AddProduct?"
                    "format=ajax", headers=headers, data=data, proxies=self.proxy,
                    timeout=5)

            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Added to cart.")
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Carting: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.cart_add()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Carting: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.cart_add()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Carting: "
                  f"Timeout. Retrying...")
            self.cart_add()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Carting: "
                  f"{error}. Retrying...")
            self.cart_add()
            return

        if self.bypass == "disabled":
            self.load_login_page()
            return
        elif self.bypass == "waiting":
            self.load_login_page()
            return
        else:
            self.load_address_page()
            return

    def load_login_page(self):
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Service-Worker-Navigation-Preload": "true",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Referer": self.product_url,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}]"
                  f" Loading login page... ")
            cart_page = self.s.get("https://www.emp-shop.pl/checkout", headers=headers,
                                   proxies=self.proxy, timeout=5)
            while "Zam&oacute;w bez rejestracji" not in cart_page.text:
                self.error_num += 1
                if self.error_num > 10:
                    print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Loading login"
                          f" error. Retrying... ")
                    self.error_num = 0
                    self.load_product_page()
                    return
                time.sleep(.1)
                cart_page = self.s.get("https://www.emp-shop.pl/checkout", headers=headers,
                                       proxies=self.proxy, timeout=5)

            self.csrf_token = re.search('csrf_token" value="(.*?)"', cart_page.text).group().split('"')[-2]
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Login page: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_login_page()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Login page: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_login_page()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Login page: "
                  f"Timeout. Retrying...")
            self.load_login_page()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Login page: "
                  f"{error}. Retrying...")
            self.load_login_page()
            return

        self.load_address_page()
        return

    def load_address_page(self):
        data = f"dwfrm_login_unregistered=Zam%C3%B3w+bez+rejestracji&" \
               f"csrf_token={self.csrf_token.replace('=', '%3D')}"
        bypass_headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Content-Length": str(len(data)),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.emp-shop.pl/checkout",
            "Origin": "https://www.emp-shop.pl",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Service-Worker-Navigation-Preload": "true",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Referer": self.product_url,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] "
                  f"Loading address page... ")
            if self.bypass == "configured":
                address_page = self.s.get("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COInit-Start",
                                          headers=headers, proxies=self.proxy, timeout=6)
            else:
                address_page = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/"
                                           "COCustomer-LoginForm?scope=checkout", data=data, headers=bypass_headers,
                                           proxies=self.proxy, timeout=6)
            while "Twoje zam&oacute;wienie" not in address_page.text:
                self.error_num += 1
                if self.error_num > 10:
                    print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Loading "
                          f"address page error. Retrying... ")
                    self.error_num = 0
                    self.load_product_page()
                    return
                time.sleep(.1)
                if self.bypass == "configured":
                    address_page = self.s.get(
                        "https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COInit-Start",
                        headers=headers, proxies=self.proxy, timeout=6)
                else:
                    address_page = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/"
                                               "COCustomer-LoginForm?scope=checkout", data=data, headers=bypass_headers,
                                               proxies=self.proxy, timeout=6)
            self.csrf_token = re.search('csrf_token" value="(.*?)"', address_page.text).group().split('"')[-2]

        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address page: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_address_page()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address page: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_address_page()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address page: "
                  f"Timeout. Retrying...")
            self.load_address_page()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address page: "
                  f"{error}. Retrying...")
            self.load_address_page()
            return

        self.send_address()
        return

    def send_address(self):
        if self.bypass == "configured":
            action_type = "edit"
        else:
            action_type = "add"

        data = f"dwfrm_profile_customer_gender=1&pcaactiontype={action_type}&billingAddress_addressType=postaladdress&" \
               f"dwfrm_billing_billingAddress_addressFields_EU3to6_firstName={self.profile['first_name']}&" \
               f"dwfrm_billing_billingAddress_addressFields_EU3to6_lastName={self.profile['last_name']}&" \
               f"pcaddress=&dwfrm_billing_billingAddress_addressFields_EU3to6_address2=&" \
               f"dwfrm_billing_billingAddress_addressFields_EU3to6_address1=" \
               f"{self.profile['street']}&" \
               f"dwfrm_billing_billingAddress_addressFields_EU3to6_houseNumber=" \
               f"{self.profile['house_number']}&" \
               f"dwfrm_billing_billingAddress_addressFields_EU3to6_postal={self.profile['post_code']}&" \
               f"dwfrm_billing_billingAddress_addressFields_EU3to6_city={self.profile['city']}&" \
               f"dwfrm_billing_billingAddress_country=PL&" \
               f"dwfrm_singleshipping_shipmentAddressSelection=billingAddress&" \
               f"dwfrm_singleshipping_shippingAddress_addressTypes_addressType=postaladdress&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_firstName=&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_lastName=&pcaddress=&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_address2=&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_address1=&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_houseNumber=&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_postal=&" \
               f"dwfrm_singleshipping_shippingAddress_addressFields_EU3to6_city=&" \
               f"dwfrm_singleshipping_shippingAddress_country=PL&dwfrm_profile_customer_birthday=2001-05-06&" \
               f"profile_customer_birthday_day=6&profile_customer_birthday_month=5&" \
               f"profile_customer_birthday_year=2001&" \
               f"dwfrm_billing_billingAddress_email_emailAddress=" \
               f"{self.profile['email']}&" \
               f"dwfrm_billing_billingAddress_email_emailAddressConfirm=" \
               f"{self.profile['email']}&" \
               f"dwfrm_profile_customer_homePhone={self.profile['phone']}&" \
               f"dwfrm_profile_customer_mobilePhone=&" \
               f"dwfrm_minishipping_shippingAddress_shippingMethodID=DHL_PL&" \
               f"dwfrm_singleshipping_shippingAddress_save=checkout.init.continue&" \
               f"csrf_token={self.csrf_token.replace('=', '%3D')}"

        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Content-Length": str(len(data)),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COInit-Start",
            "Origin": "https://www.emp-shop.pl",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Sending address... ")
            address_post = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COInit-Init",
                                       data=data, headers=headers, proxies=self.proxy, timeout=5)

            while "Płatność" not in address_post.text:
                self.error_num += 1
                if self.error_num > 10:
                    print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Filling "
                          f"address error. Retrying... ")
                    self.error_num = 0
                    self.load_product_page()
                    return
                time.sleep(.1)
                address_post = self.s.post(
                    "https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COInit-Init",
                    data=data, headers=headers, proxies=self.proxy, timeout=5)

            self.csrf_token = re.search('csrf_token" value="(.*?)"', address_post.text).group().split('"')[-2]
            if "Płatność za pobraniem" in address_post.text:
                self.payment = "CASH_ON_DELIVERY"
            else:
                self.payment = "PAYMENT_IN_ADVANCE"
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address post: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.send_address()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address post: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.send_address()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address post: "
                  f"Timeout. Retrying...")
            self.send_address()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Address post: "
                  f"{error}. Retrying...")
            self.send_address()
            return

        if self.bypass == "waiting":
            self.load_cart_page()
            return
        else:
            self.send_payment()
            return

    def load_cart_page(self):
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Service-Worker-Navigation-Preload": "true",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            cart_page = self.s.get("https://www.emp-shop.pl/cart", headers=headers, proxies=self.proxy, timeout=6)
            self.csrf_token = re.search('csrf_token" value="(.*?)"', cart_page.text).group().split('"')[-2]

        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Cart page: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_cart_page()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Cart page: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.load_cart_page()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Cart page: "
                  f"Timeout. Retrying...")
            self.load_cart_page()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Cart page: "
                  f"{error}. Retrying...")
            self.load_cart_page()
            return

        self.bypass_item_delete()
        return

    def bypass_item_delete(self):
        data = f"dwfrm_cart_shipments_i0_items_i0_quantity=1&dwfrm_cart_shipments_i0_items_i0_quantity=1&" \
               f"dwfrm_cart_shipments_i0_items_i0_deleteProduct=Remove&" \
               f"dwfrm_cart_updateCart=dwfrm_cart_updateCart&csrf_token={self.csrf_token.replace('=', '%3D')}"
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Content-Length": str(len(data)),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
                      "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.emp-shop.pl/cart",
            "Origin": "https://www.emp-shop.pl",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Removing bypass "
                  f"item from cart...")
            item_delete = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/"
                                      "Cart-SubmitForm", headers=headers, data=data, proxies=self.proxy, timeout=6)
            while "Koszyk jest pusty" not in item_delete.text:
                time.sleep(.1)
                item_delete = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/"
                                          "Cart-SubmitForm", headers=headers, data=data, proxies=self.proxy, timeout=6)

        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Bypass item removal: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.bypass_item_delete()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Bypass item removal: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.bypass_item_delete()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Bypass item removal: "
                  f"Timeout. Retrying...")
            self.bypass_item_delete()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Bypass item removal: "
                  f"{error}. Retrying...")
            self.bypass_item_delete()
            return

        self.bypass = "configured"
        self.wait_for_product()
        return

    def send_payment(self):

        data = f"dwfrm_wirecardcredit_type=&dwfrm_wirecardcredit_number=&dwfrm_wirecardcredit_month=1&" \
               f"dwfrm_wirecardcredit_year=2019&dwfrm_wirecardcredit_carduuid=&" \
               f"dwfrm_minibilling_paymentMethods_selectedPaymentMethodID={self.payment}&" \
               f"dwfrm_minibilling_paymentMethods_creditCard_owner=&" \
               f"dwfrm_minibilling_paymentMethods_creditCard_type=Visa&" \
               f"dwfrm_minibilling_paymentMethods_creditCard_number_d0bkalhddxoa=&" \
               f"dwfrm_minibilling_paymentMethods_creditCard_expiration_month=1&" \
               f"dwfrm_minibilling_paymentMethods_creditCard_expiration_year=2016&" \
               f"dwfrm_minibilling_paymentMethods_creditCard_cvn_d0furetkfgxr=&" \
               f"dwfrm_minibilling_couponCode=&csrf_token={self.csrf_token.replace('=', '%3D')}&" \
               f"dwfrm_minibilling_save=CONTINUE&ajaxUpdate=1"

        # karta
        # data = f"dwfrm_minibilling_paymentMethods_selectedPaymentMethodID=WIRECARD_CREDIT&" \
        #        f"dwfrm_wirecardcredit_type=visa&dwfrm_wirecardcredit_number=****************464&" \
        #        f"dwfrm_wirecardcredit_month=8&dwfrm_wirecardcredit_year=2020&" \
        #        f"dwfrm_wirecardcredit_carduuid=***&" \
        #        f"dwfrm_minibilling_paymentMethods_creditCard_owner=&" \
        #        f"dwfrm_minibilling_paymentMethods_creditCard_type=Visa&" \
        #        f"dwfrm_minibilling_paymentMethods_creditCard_number_d0sfqwedumrc=&" \
        #        f"dwfrm_minibilling_paymentMethods_creditCard_expiration_month=1&" \
        #        f"dwfrm_minibilling_paymentMethods_creditCard_expiration_year=2016&" \
        #        f"dwfrm_minibilling_paymentMethods_creditCard_cvn_d0fwjxibtevp=&" \
        #        f"dwfrm_minibilling_couponCode=&csrf_token=&" \
        #        f"dwfrm_minibilling_save=CONTINUE&ajaxUpdate=1"

        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/83.0.4103.116 Safari/537.36",
            "Content-Length": str(len(data)),
            "Accept": "*/*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "ADRUM": "isAjax:true",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://www.emp-shop.pl/billing",
            "Origin": "https://www.emp-shop.pl",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Sending payment... ")
            payment_post = self.s.post("https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COBilling-Bil"
                                       "ling", data=data, headers=headers, proxies=self.proxy, timeout=5)

            while "Zam&oacute;w" not in payment_post.text:
                self.error_num += 1
                if self.error_num > 10:
                    print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Payment error."
                          f" Retrying... ")
                    self.error_num = 0
                    self.load_product_page()
                    return
                time.sleep(.1)
                payment_post = self.s.post(
                    "https://www.emp-shop.pl/on/demandware.store/Sites-GLB-Site/pl_PL/COBilling-Bil"
                    "ling", data=data, headers=headers, proxies=self.proxy, timeout=5)

            tokens = re.findall('csrf_token" value="(.*?)"', payment_post.text)
            self.checkout_data = f"clientDeviceType=desktop&csrf_token={tokens[0].replace('=', '%3D')}&" \
                                 f"mobilePhoneRequired=1&dwfrm_profile_customer_mobilePhone={self.profile['phone']}&" \
                                 f"csrf_token={tokens[1].replace('=', '%3D')}"
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Payment post: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.send_payment()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Payment post: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.send_payment()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Payment post: "
                  f"Timeout. Retrying...")
            self.send_payment()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Payment post: "
                  f"{error}. Retrying...")
            self.send_payment()
            return

        self.send_checkout()
        return

    def send_checkout(self):
        headers = {
            "Host": "www.emp-shop.pl",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
            "Content-Length": str(len(self.checkout_data)),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/"
                      "apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.emp-shop.pl/revieworder",
            "Origin": "https://www.emp-shop.pl",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Checking out... ")
            checkout_page = self.s.post("https://www.emp-shop.pl/orderconfirmation", data=self.checkout_data,
                                        headers=headers, proxies=self.proxy, timeout=5)
            while "Dziękujemy!" not in checkout_page.text:
                self.error_num += 1
                if self.error_num > 10:
                    print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Checkout "
                          f"error. Retrying... ")
                    self.error_num = 0
                    self.load_product_page()
                    return
                time.sleep(.1)
                checkout_page = self.s.post("https://www.emp-shop.pl/orderconfirmation", data=self.checkout_data,
                                            headers=headers, proxies=self.proxy, timeout=5)
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Successful checkout. "
                  f"Email: {self.profile['email'].replace('%40', '@')}.")
        except requests.exceptions.ConnectionError:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Checkout: "
                  f"Connection Error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.send_checkout()
            return
        except requests.exceptions.RequestException:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Checkout: "
                  f"Request error. Rotating proxy...")
            self.proxy = self.queue.get_proxy()
            self.send_checkout()
            return
        except requests.exceptions.Timeout:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Checkout: "
                  f"Timeout. Retrying...")
            self.send_checkout()
            return
        except Exception as error:
            print(f"{datetime.datetime.now().strftime('[%H:%M:%S:%f]')} [TASK {self.task['id']}] Checkout: "
                  f"{error}. Retrying...")
            self.send_checkout()
            return

        return


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class QueueProxy(Queue, metaclass=Singleton):
    pass


class ProxyInput(object):

    def __init__(self, proxy):
        self.queue = QueueProxy()
        self.proxy = proxy

    def run(self):
        self.queue.put(self.proxy)


class Interpreter(object):

    def __init__(self):
        self.queue = QueueProxy()

    def get_proxy(self):
        return self.queue.get()


def main(curr_task, curr_profile):
    new_task = EmpShop(curr_task, curr_profile)
    new_task.wait_for_product()


if __name__ == "__main__":
    with open("USER_INPUT_DATA/tasks.json", "r") as f1, \
            open("USER_INPUT_DATA/proxies.txt", "r") as f2, \
            open("USER_INPUT_DATA/profiles.json", "r") as f3:
        settings = json.load(f1)
        proxies = f2.read().split("\n")
        profiles = json.load(f3)
    threads = []
    for proxy in proxies:
        proxy_list = proxy.split(":")
        proxy_dict = {
            "http": f"http://{proxy_list[2]}:{proxy_list[3]}@{proxy_list[0]}:{proxy_list[1]}",
            "https": f"https://{proxy_list[2]}:{proxy_list[3]}@{proxy_list[0]}:{proxy_list[1]}"
        }
        add_proxy = ProxyInput(proxy_dict)
        add_proxy.run()
    with ThreadPoolExecutor(max_workers=len(settings)) as executor:
        futures = []
        for i in range(len(settings)):
            task_data = [settings[i], profiles[i]]
            futures.append(executor.submit(lambda p: main(*p), task_data))
        results = []
        for result in as_completed(futures):
            results.append(result)
