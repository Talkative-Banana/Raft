import os
import grpc
import time
import json
import random
from concurrent import futures
import threading
import logging
import sys
import election_pb2
import election_pb2_grpc

class Client:
    Nodes = {1: ["localhost", 8501], 2 : ["localhost", 8502], 3 : ["localhost", 8503], 4 : ["localhost", 8504], 5 : ["localhost", 8505]}
    def __init__(self, ipaddr, port):
        self.ipaddr = ipaddr
        self.port = port
        self.leaderid = None

    def set(self, k, v):
        if((self.leaderid == None)):
            self.leaderid = self.getleader()
        
        if(self.leaderid == None):
            return "Could not contact Leader", False
        
        channel = grpc.insecure_channel((self.Nodes[self.leaderid])[0] + ":" + str((self.Nodes[self.leaderid])[1]))
        stub = election_pb2_grpc.ElectionStub(channel)
        try:
            req = f"{k} {v}"
            response = stub.ServeClient(election_pb2.ServeClientArgs(Request=req))
            if response.Success:
                return "Success", True
            else:
                return response.Data, False
        
        except: # Leader Inactive or out of reach
            self.getleader()
            return self.set(k, v)
    
    def ServeClient(self, request, context):
        return request
    
    def getleader(self):
        for node in self.Nodes:
            try:
                channel = grpc.insecure_channel(self.Nodes[node][0] + ":" + str(self.Nodes[node][1]))
                stub = election_pb2_grpc.ElectionStub(channel)
                req=""
                response = stub.ServeClient(election_pb2.ServeClientArgs(Request=req))
                if(response.LeaderID != "None"):
                    self.leaderid = int(response.LeaderID)
                    return self.leaderid
                
            except:
                print(f"Node {node} is not reachable")
        return None # Couldnot find leader

    def get(self, k):
        if((self.leaderid == None)):
            self.leaderid = self.getleader()

        if(self.leaderid == None):
            print("Could not contact Leader")
            return None

        channel = grpc.insecure_channel(self.Nodes[self.leaderid][0] + ":" + str(self.Nodes[self.leaderid][1]))
        stub = election_pb2_grpc.ElectionStub(channel)
        try:
            req = str(k)
            response = stub.ServeClient(election_pb2.ServeClientArgs(Request=req))
            if response.Success:
                return response.Data
            else:
                self.leaderid = int(response.LeaderID)
                return None
    
        except: # Leader Inactive or out of reach
            self.getleader()
            return self.get(k)
    
def serve(client, ip_addr, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    election_pb2_grpc.add_ElectionServicer_to_server(client, server)
    server.add_insecure_port(ip_addr + ":" + str(port))
    server.start()
    server.wait_for_termination()
    
def main():
    if(len(sys.argv) != 3):
        print("Invalid arguments (client.py [ip_addr] [port])")
        return 1
    ipadd = sys.argv[1]
    port = sys.argv[2]
    client = Client(ipadd, port)
    while(1):
        print("1) Set")
        print("2) Get")
        print("3) Exit")
        inp = int(input("Enter choice: "))
        if inp == 1:
            k = input("Enter K: ")
            v = int(input("Enter V: "))
            val, flag = client.set(k, v)
            if not flag: print(val)
        elif inp == 2:
            k = input("Enter K: ")
            val = client.get(k)
            if val == None:
                print("None")
                continue
            if(val == ""):
                print("K not found!")
            else:
                print("Value of K:", val)
        elif inp == 3:
            break
        else:
            print("Invalid Input")
    serve(client, ipadd, port)
    return

if __name__ == "__main__": main()