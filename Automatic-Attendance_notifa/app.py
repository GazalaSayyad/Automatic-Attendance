from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import schedule
from errno import ENETUNREACH
from quoters import Quote
import datetime, configparser
import geocoder, json
import time, requests

class Base:

    __FILE__ = 'config.ini'

    def __init__(self):
        self.cfg = self.setup_config(Base.__FILE__)

    def setup_config(self, config_filename):
        configParser   = configparser.RawConfigParser()   
        configParser.read(config_filename)
        return configParser

class AutoZohoAttendence(Base):

    __URL__     = 'https://peopleplus.zoho.in/neurapses/zp#attendance/entry/listview'

    def __init__(self):
        Base.__init__(self)
        self.driver  = None
        self.waiting = 20 
        self.__notification_url__ = self.cfg['flask_notification_systemd']['ip']

    def notification(self,urgency,title,message):
        payload = {
            "urgency":urgency,
            "title":title,
            "message":message
        }
        payload = json.dumps(payload)
        headers = {'Content-Type': 'application/json'}
        response = requests.request("POST", self.__notification_url__, headers=headers, data=payload)
        print(response)

    def web_driver_load(self):
        lat, lng = self.get_latlng()
        geo = webdriver.FirefoxOptions()
        geo.add_argument("--headless")
        geo.set_preference("geo.enabled", True)
        geo.set_preference('geo.prompt.testing', True)
        geo.set_preference('geo.prompt.testing.allow', True)
        location = 'data:application/json,{"location": {"lat": %s, "lng": %s}, "accuracy": 100.0}'
        location = (location)%(lat,lng)
        geo.set_preference('geo.provider.network.url', location)
        self.driver = webdriver.Firefox(firefox_profile='/app/profile', options=geo)

    def test_internet(self, silent=False):
        while True:
            try:
                requests.get('https://www.google.com/').status_code
                if not silent:
                    self.notification("normal",\
                                "internet connection ok",
                                "internet connection working good")
                break
            except:
                time.sleep(15)
                self.notification("critical",\
                              "No internet connection",
                              "please check your internet connectivity.....")
                pass

    def web_driver_quit(self):
        if self.driver!= None: self.driver.quit()

    def get_latlng(self):
        g = geocoder.ip('me')
        val = g.latlng
        lat, lng = val[0], val[1]
        return lat, lng
    
    def test(self):
        try:
            res = False
            self.test_internet()
            self.web_driver_load()
            self.driver.get(AutoZohoAttendence.__URL__)
            web_obj = self.driver.find_element_by_xpath('/html/body/div[2]/div[2]/div/div/div[2]/div/button[3]/div/div[3]')
            val = web_obj.text
            _, _ = val.split("\n")
            self.notification("normal",\
                              "Hi!! Automated attendance testing done..........",
                              "Looks like all good to go! yuppp")
            res = True
        except NoSuchElementException:
            self.notification("critical",\
                              "Zoho Attendence Login Failed!",
                              "Session has Expired Need to Login in Zoho Attendence page in you firefox Profile!")
        except Exception as e:
            self.notification("critical", \
                              "Attendence Failed", \
                              "This profile was last used with a newer version of this application. Please create a new Firefox profile")
        finally:
            self.web_driver_quit()
            return res

    def open_zoho__attendence_page(self,entry_type, is_late=False):
        try:
            self.test_internet(silent=True)
            self.web_driver_load()
            if (entry_type == 'Check-in') and (not is_late):
               quote = Quote.print()
               self.notification("normal",\
                                 "Good Morning! Have a good day ahead!", \
                                 quote )
            if (entry_type == 'Check-out') and (not is_late):
               quote = Quote.print()
               self.notification("normal",\
                                 "Hey there!! it is time to take rest", \
                                 quote )            
            self.driver.get(AutoZohoAttendence.__URL__)
            web_obj = self.driver.find_element_by_xpath('/html/body/div[2]/div[2]/div/div/div[2]/div/button[3]/div/div[3]')
            val = web_obj.text
            _status, _ = val.split("\n")
            if _status == entry_type:  
                web_obj.click()
                self.notification("normal",\
                                  "Today's {} Done".format(entry_type), \
                                  "Thank me later..you have missed your {}! I have done for you".format(entry_type) )  
                time.sleep(10)
            elif (entry_type == 'Check-in') and (_status=='Check-out'):
                self.notification("normal",\
                                  "Good work!!", \
                                  "Already Check-in done!!")
                time.sleep(10)
            elif (entry_type == 'Check-out') and (_status=='Check-in'):
                self.notification("normal",\
                                  "Good work!!", \
                                  "Already Check-out done!!")
                time.sleep(10)
            else:
                pass
        except NoSuchElementException:
            self.notification("critical",\
                              "Zoho Attendence Login Failed!",
                              "Session has Expired Need to Login in Zoho Attendence page in you firefox Profile!")
        except Exception as e:
            self.notification("critical", \
                              "Attendence Failed", \
                              "This profile was last used with a newer version of this application. Please create a new Firefox profile")
        finally:
            self.web_driver_quit()
    
    def attendence(self,entry_type,is_late=False):
        if self.driver!= None: self.driver.quit()
        self.open_zoho__attendence_page(entry_type,is_late=is_late)

def job(entry_type,is_late=False):
    if datetime.datetime.today().strftime('%A') not in exclude_day:
        az.attendence(entry_type,is_late=is_late)

def warm_up(start_time,end_time):
    if datetime.datetime.today().strftime('%A') not in exclude_day:
        machine_on_time = datetime.datetime.now().time()
        checkin_time    = datetime.datetime.strptime(start_time, '%H:%M').time()
        checkout_time   = datetime.datetime.strptime(end_time, '%H:%M').time()
        if ( machine_on_time < checkin_time ) and ( machine_on_time < checkout_time ):
            pass
        if ( machine_on_time > checkin_time ) and ( machine_on_time < checkout_time ):
            az.notification(urgency='critical', \
                            title='Late Check-in', \
                            message='Hey there!!....another late entry!!...dont worry let me mark your entry if you have not done yet')
            az.attendence(entry_type='Check-in',is_late=True)
        if ( machine_on_time > checkout_time ):
            az.notification(urgency='critical', \
                            title='Late Check-out', \
                            message='Hey there!!....another late entry!!...dont worry let me mark your entry if you have not done yet')
            az.attendence(entry_type='Check-out', is_late=True)


az = AutoZohoAttendence()

exclude_day = ['Saturday','Sunday']
start_time  = "10:00"
end_time    = "19:00"

if __name__ == "__main__":
    if az.test():
        az.notification(urgency='normal', \
                        title='Automated attendance started! => {}'.format(str(datetime.datetime.now())), \
                        message="Hey there!! daemon automated attendance start! your Check-in and Check-out time is monitoring and mark accordingly!")
        warm_up(start_time,end_time)
        schedule.every().day.at(start_time).do(job,'Check-in')
        schedule.every().day.at(end_time).do(job,'Check-out')
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        az.notification(urgency='critical', \
                        title='Automated attendance Failed to start for today! => {}'.format(str(datetime.datetime.now())), \
                        message="Sorry! looks like some internal issue! Do your attendence manualy! try for next few days! if continue persists please contact with the creator!!")