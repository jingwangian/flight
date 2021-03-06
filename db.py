#!/usr/local/bin/python3
# Copyright (C) 2015-2025 Wang,Jing   <jingwangian@gmail.com>
#
# This file is part of Flight Inforation Query System (fiqs)
#
# fiqs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# fiqs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with fiqs.  If not, see <http://www.gnu.org/licenses/>.

import psycopg2
import datetime
import url
import logging

main_logger = None

class DBError(Exception):
    def __init__(self,reason="unknown"):
        self.reason = reason
    
class FlightPlanDatabase():
    def __init__(self,database='flight_db',user='wangj', host='localhost', port=5432):
        self.database=database
        self.user=user
        self.host=host
        self.port=port
        self.conn=None
        self.connected = False
        
    def __del__(self):
        if self.connected==True:
            self.disconnectDB()
    
    def connectDB(self):
        try:
            self.conn = psycopg2.connect(database=self.database,
                                        user=self.user,
                                        host=self.host,
                                        port=self.port)
            self.connected = True
        except psycopg2.OperationalError:
            raise DBError("Failed to connetc to DB")
            
    def disconnectDB(self):
        try:
            self.conn.close()
        except:
            raise DBError("Failed to close connection to DB")
        finally:
            self.connected = False
            
    def create_new_fligt_schedule(self):
        '''
        Create today's flight schedule
        '''
        cur = self.conn.cursor()
        cur.execute('select count(*) from flight_view')
        col = cur.fetchone()
        if col==None:
            print("no return data")
        else:
            if col[0] == 0:
                print("no today's date")
                self.create_today_flight_schedule()
                
        cur.close()
        
    def create_today_flight_schedule(self):
        sql_cmd='''INSERT INTO flight 
                SELECT 
                    nextval('flight_id') as id,
                    from_city,
                    to_city,
                    trip,
                    (current_date+start_day) as start_date,
                    (current_date+start_day+stay_days) as return_date,
                    adults,
                    children,
                    children_age,
                    cabinclass,
                    current_date
                FROM airline;'''
        
        print(sql_cmd)
        cur = self.conn.cursor()
        cur.execute(sql_cmd)
        self.conn.commit()
        cur.close()

    def get_flight_schedule(self, start_date=None,range=1):
        """
        Read the tuples from the flight database.
        start_date --- must be a date
        
        Put the result into a list in which every item is a dict type.
        The dict is as following:
        flight['id']
        flight['from']
        flight['to']
        flight['trip']
        flight['start_date']
        flight['return_date']
        flight['adults']
        flight['children']
        flight['children_age']
        flight['cabinclass']"""
        
        airline_list=[]
        cur = self.conn.cursor()
        if start_date is None:
            cur.execute('select * from flight_view order by id')
        else:
            end_date = start_date+datetime.timedelta(range)
            print(start_date)
            print(end_date)
            cur.execute("select * from flight_view where start_date>=%s and start_date<%s order by id", (start_date,end_date))
        
        while(1):
            col = cur.fetchone()
            if col==None:
                break;
            else:
                flight={}
                flight['id']=col[0]
                flight['from'] = col[1]
                flight['to'] = col[2]
                flight['trip'] = col[3]
                flight['start_date'] = col[4]
                flight['return_date'] = col[5]
                flight['adults'] = col[7]
                flight['children'] = 0
                flight['children_age'] = '{}'
                flight['cabinclass'] = col[8]             
                airline_list.append(flight)
                
        cur.close()
        
        return airline_list
        
    def get_flight_by_id(self, id):
        cur = self.conn.cursor()
        cur.execute('''select id,
                    flight_view.from,
                    flight_view.to,
                    trip,
                    start_date,
                    stay_days,
                    adults,
                    children,
                    age,
                    class 
                    from flight_view where id=%s''', (id,))
        
        tup = cur.fetchone()
        flight={}
        flight['id']=tup[0]
        flight['from'] = tup[1]
        flight['to'] = tup[2]
        flight['trip'] = tup[3]
        flight['start_date'] = tup[4]
        flight['return_date'] = tup[4]
        flight['stay_days'] = tup[5]
        flight['adults'] = tup[6]
        flight['children'] = tup[7]
        flight['children_age'] = tup[8]
        flight['cabinclass'] = tup[9]
        
        cur.close()
        
        return flight

    def get_flight_url_by_id(self, id):
        req_url = None

        cur = self.conn.cursor()
        
        try:
            cur.execute('''select id,
                        flight_url_view.from,
                        flight_url_view.to,
                        trip,
                        start_date,
                        stay_days,
                        adults,
                        children,
                        age,
                        class 
                        from flight_url_view where id=%s''', (id,))
            
            tup = cur.fetchone()
            flight={}
            flight['id']=tup[0]
            flight['from'] = tup[1]
            flight['to'] = tup[2]
            flight['trip'] = tup[3]
            flight['start_date'] = tup[4]
            flight['return_date'] = tup[4]
            flight['stay_days'] = tup[5]
            flight['adults'] = tup[6]
            flight['children'] = tup[7]
            flight['children_age'] = tup[8]
            flight['cabinclass'] = tup[9]
            
            url_creater=url.ExpediaReqURL()
            req_url = url_creater.createURL(**flight)
        finally:
            cur.close()
        
        return req_url

    def add_into_flight_price_tbl(self, flight_info):
        """
        Insert one result for flight price into flight_price table
        """
        cur = self.conn.cursor()
        
#         print('company --- %s' %flight_info['company'])
        try:
        
            cur.execute('''SELECT * FROM get_airline_company_id_by_name(%s)''',(flight_info['company'],))
            
            
            company_tuple=cur.fetchone()
            company_id=company_tuple[0]
            
            cur.execute('''INSERT INTO flight_price 
                           (flight_id,price,company_id,departure_time,arrival_time,duration,span_days,stop,stop_info,search_date)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);''',
                            (flight_info['id'],
                             flight_info['price'],
                             company_id,
                             flight_info['dep_time'],
                             flight_info['arr_time'],
                             flight_info['duration'],
                             flight_info['span_days'],
                             flight_info['stop'],
                             flight_info['stop_info'],
                             flight_info['search_date']))
            
            self.conn.commit()
        except Exception as e:
            print('db error in add_into_flight_price_tbl: %s' %e)
                
        finally:
            cur.close()
            
    def create_today_task(self):
        """
        Create today's task by select flight_id into flight_price_query_task.
        """
        total_task_num = 0

        cur = self.conn.cursor()
        try:
            cur.execute('''DELETE FROM flight_price_query_task where execute_date<current_date;''')
            cur.execute('''SELECT count(*) from flight_price_query_task where execute_date=current_date;''')
            col = cur.fetchone()
            num = col[0]
            if num<1:
                cur.execute('''insert into flight_price_query_task select id,0,current_date from flight where start_date>current_date;''')
                self.conn.commit()
                cur.execute('''SELECT count(*) from flight_price_query_task where execute_date=current_date;''')
                col = cur.fetchone()
                total_task_num = col[0]
        finally:
            cur.close()
            return total_task_num            
    
    def get_one_task_id(self):
        """
        Get one flight_id from flight_price_query_task where execute_date is
        current_date.
        Return a task_list include all flight_id.
        """
        
        cur = self.conn.cursor()
        cur.execute('''Select flight_id from flight_price_query_task 
                        where execute_date=current_date and status = 0 
                        order by flight_id limit 1''')

        col = cur.fetchone()
        
        if col == None:
            return None
        
        flight_id = col[0]
        
        return flight_id
        
    def get_today_task_id(self,limit_number=1000):
        """
        Get all flight_id from flight_price_query_task where execute_date is
        current_date.
        Return a task_list include all flight_id.
        """
        cur = self.conn.cursor()
        cur.execute('''Select flight_id from flight_price_query_task 
                        where execute_date=current_date and status <> 2 
                        order by flight_id limit %s;''',(limit_number,))

        task_list=[]
        
        while(1):
            col = cur.fetchone()
            if col==None:
                break;
            else:
                task_list.append(col[0])
                
        cur.close()
        
        return task_list
    
    def update_status_in_flight_price_query_task_tbl(self, flight_id, status, search_date):
        """
        update the flight_price_query_task table, set the status to 1 
        for the flight_id = flight_id.
        """
        cur = self.conn.cursor()
        
        cur.execute('''update flight_price_query_task set status=%s 
                    where flight_id=%s and execute_date=%s;''',
                    (status,flight_id,search_date))
        self.conn.commit()
        cur.close()
        
    def add_one_group_flight_schedule(self,start_date,start_date_range):
        """
        This function add a group fligth schedule which start_date will be in 
        a list of start_date_list
        """
        
        cur = self.conn.cursor()
        for i in range(0,start_date_range):
            sd_date = start_date+datetime.timedelta(i)
            sd_str = sd_date.strftime("%Y-%m-%d")
            cur.execute('''select count(*) from flight where start_date=%s''',(sd_str,))
            col = cur.fetchone()
            num = int(col[0])
            if num > 0:
                continue
            cur.execute('''select create_one_way_airlines(%s)''',(sd_str,))
            self.conn.commit()
        cur.close()
        
def test():
    fdb = FlightPlanDatabase()
  
    u = url.ExpediaReqURL()
    
    try:
        fdb.connectDB()
        task_id = fdb.get_one_task_id()
    
        print(task_id)
        flight = fdb.get_flight_by_id(task_id)
        req_url = u.createURL(**flight)
        print(req_url)
    
        fdb.disconnectDB()

    except DBError as err:
        print("Error: %s" % str(err))
    
def test_add_flight_schedule():
    fdb = FlightPlanDatabase()
    try:
        fdb.connectDB()
        
        start_date=datetime.date.today()+datetime.timedelta(1)
        start_date_range=90
        
        flight = fdb.add_one_group_flight_schedule(start_date,start_date_range)
    
        fdb.disconnectDB()

    except DBError as err:
        print("Error: %s" % str(err))    

def create_today_flight_schedule():
    fdb = FlightPlanDatabase()
    try:
        fdb.connectDB()
        
        start_date=datetime.date.today()+datetime.timedelta(1)
        start_date_range=180   #Create 180 days data
        
        fdb.add_one_group_flight_schedule(start_date,start_date_range)
        
        fdb.create_today_task()

    except DBError as err:
        print("Error: %s" % str(err))
    finally:
        fdb.disconnectDB()

def init_log():
    """
    #Init the main logger
    """
    global logger_handle
    
    d = str(datetime.date.today())
    t1 = datetime.datetime.now()
    logname='log/air_'+d+'.log'
    logger_handle=logging.FileHandler(logname)
    
    formatter = logging.Formatter('%(levelname)s: %(asctime)s %(message)s')
    
    logger_handle.setFormatter(formatter)
    
    main_logger=logging.getLogger('[Main]')
    main_logger.addHandler(logger_handle)
    main_logger.setLevel('INFO')
    
    worker_logger= logging.getLogger('[Worker]')
    worker_logger.setLevel('INFO')
    worker_logger.addHandler(logger_handle)
    
    return main_logger
            
def main():
    init_log()
    create_today_flight_schedule()
#     test_get_flight_url_by_id()
    

def test_get_flight_url_by_id():
    
    fdb = FlightPlanDatabase()
    try:
        fdb.connectDB()
        
        for id in range(1,31):
            req_url = fdb.get_flight_url_by_id(id)
            print(req_url)

    except DBError as err:
        print("Error: %s" % str(err))
    finally:
        fdb.disconnectDB() 

if __name__=='__main__':
    main()
