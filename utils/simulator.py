"""
Author: Ali Mokhtari (ali.mokhtaary@gmail.com)
Created on Jan, 18, 2022
"""
import sys
import pandas as pd
import matplotlib.pyplot as plt

import utils.config as config
from utils.application import Application, AppStatus
from utils.event import Event, EventTypes



class Simulator:
    

    def __init__(self):                             
        self.stats = {'missed':0,}
        



    def read_workload(self, workload_id):
        path_to_workload = f'{config.path_to_workloads}/workload-{workload_id}.csv'
        workload = pd.read_csv(path_to_workload)
        return workload 
    
    def initialize(self, workload_id):
        workload = self.read_workload(workload_id)        
        for _, request in workload.iterrows():  
            app_name = request[0]
            request_time = request[1]          
            app = config.find_app(app_name)
            event_time = request_time - config.window
            event = Event(event_time, EventTypes.STARTED, app)
            config.event_queue.add_event(event)

    
    def run(self):
        while config.event_queue.event_list:
            event = config.event_queue.get_first_event()
            app = event.event_details
            config.time.set_time(event.time)
            s = f'\n\nEvent: {event.event_type.name} @{event.time:3.1f}\n'
            s += f'--- App:{app.name} Free:{config.memory.free}\n'
            s += '=======================================================\n'


            if event.event_type == EventTypes.STARTED:
                if app.status != AppStatus.AGGRESSIVE:                         
                    self.allocate(app, event.time)
                else:
                    for e in config.event_queue.event_list:
                        if e.event_type == EventTypes.FINISHED and e.event_details.name == app.name:
                            config.event_queue.remove(e)
                            app.finish_time = config.time.get_time() + 2 * config.window
                            app.stats['finish_times'][-1] = app.finish_time
                            new_event = Event(app.finish_time, EventTypes.FINISHED, app)
                            config.event_queue.add_event(new_event)
                            break


                s += f'Allocated: {app.loaded_model_size} Free:{config.memory.size}'
            
            elif event.event_type == EventTypes.FINISHED:
                app.status = AppStatus.MINIMAL
                s += f'Allocated: {app.loaded_model_size} Free:{config.memory.size}'
        
            config.log.write(s)
         

    def allocate(self, app, time):
        allocated = False  
        for best_model_size in reversed(app.models):

            if best_model_size == app.loaded_model_size:
                app.status = AppStatus.AGGRESSIVE
                app.start_time = time             
                app.finish_time = time + 2*config.window 
                event = Event(app.finish_time, EventTypes.FINISHED, app)
                config.event_queue.add_event(event)
                allocated = True
                #print(f'{app.name} @{time} : best model is there')
                break
                                                
            else:
                config.memory.release(app.loaded_model_size)
                app.loaded_model_size = 0.0
                #print(f'{app.name} @{time} : no model')

            if best_model_size <= config.memory.free :
                config.memory.allocate(best_model_size)
                app.status = AppStatus.AGGRESSIVE
                app.loaded_model_size = best_model_size
                app.finish_time = time + 2*config.window 
                event = Event(app.finish_time, EventTypes.FINISHED, app)
                config.event_queue.add_event(event)
                allocated = True                
                break      

            else:
                is_enough_space = self.evict_apps(best_model_size)
                if is_enough_space:
                    config.memory.allocate(best_model_size)
                    app.status = AppStatus.AGGRESSIVE
                    app.start_time = time             
                    app.finish_time = time + 2*config.window 
                    app.loaded_model_size = best_model_size
                    event = Event(app.finish_time, EventTypes.FINISHED, app)
                    config.event_queue.add_event(event)
                    allocated = True
                    break
            
        app.stats['requested_times'].append(time)
        app.stats['finish_times'].append(app.finish_time)        
        app.stats['evicted_times'].append(None)
        app.stats['allocated_memory'].append(app.loaded_model_size)
        
        if not allocated: 
            self.stats['missed'] += 1
         

    def evict_apps(self, required_memory):        
        candids = self.candidates_for_evicting()        
        candids.sort(reverse =True)
        
        for candid in candids:
            config.memory.release(candid.loaded_model_size)
            candid.loaded_model_size = 0.0 
            candid.status = AppStatus.MINIMAL
            candid.evict_time = config.time.get_time()

            candid.stats['requested_times'].append(None)
            candid.stats['finish_times'].append(None)
            candid.stats['evicted_times'].append(candid.evict_time)
            candid.stats['allocated_memory'].append(candid.loaded_model_size)
            
            if config.memory.free >= required_memory:
                break    
        
        is_enough_space = (required_memory <= config.memory.free)
        return is_enough_space

    def candidates_for_evicting(self):
        candids = []
        for app in  config.apps:
            if app.status != AppStatus.AGGRESSIVE and app.loaded_model_size >0.0:
                candids.append(app)        
        
        return candids
    
    def report(self):
        df_report = pd.DataFrame(columns = ['app','requested_times','finish_times',
        'evicted_times','allocated_memory','best_model'])
        
        for app in config.apps:
            
            df = pd.DataFrame(app.stats)            
            df['app'] = app.name
            df['best_model'] = app.models[-1]
            df_report = df_report.append(df, ignore_index=True)
        
        
        max_request_time = df_report['requested_times'].max()
        for app in config.apps:
            app.stats['requested_times'].insert(0,0.0)
            app.stats['allocated_memory'].insert(0,0.0)

            app.stats['requested_times'].append(max_request_time)
            app.stats['allocated_memory'].append(app.loaded_model_size)


        df_report = df_report.sort_values(by=['requested_times'])
        df_report = df_report.reset_index(drop=True)               
        df_report.to_csv('./output/report.csv', index =False)
    
    def plot_mem_usage(self):
        plt.figure()
        for app in config.apps:                     
            plt.step(app.stats['requested_times'], app.stats['allocated_memory'], '-o',where='post',label = app.name)
        plt.legend()
        plt.xlabel('Time')
        plt.ylabel('Memory Usage')
        plt.show()
