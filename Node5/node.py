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
import election_pb2
import election_pb2_grpc

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class Node(election_pb2_grpc.ElectionServicer):
    # A dictionary contaning [node_id: [ipaddr, port]] key value pairs
    Nodes = {1: ["localhost", 8501], 2 : ["localhost", 8502], 3 : ["localhost", 8503], 4 : ["localhost", 8504], 5 : ["localhost", 8505]}
    def savedump(self, txt):
        with open("dump", "+a") as file:
            file.write(txt+"\n")
        file.close()
        return
    
    def savemetadata(self):
        data = {
            "cmtlen": self.cmtlen,
            "term": self.current_term,
            "votedfor": self.voted_for
        }
        with open("metadata", "w") as file:
            json.dump(data, file)
        file.close()
        return 
    
    def loadmetadata(self):
        data = None
        with open("metadata", "r") as file:
            data = json.load(file)
        if len(data) != 3:
            print("Could not load metadata")
            exit(1)
        file.close()
        return data
    
    def __init__(self, node_id, ipaddr, port, type):
        self.node_id = node_id
        self.total_nodes = len(self.Nodes)
        self.ipaddr = ipaddr
        self.port = port
        self.data = {}
        if type == "initalize": # Initalize
            with open(f"logs_node_{node_id}", "w") as file: pass
            file.close()
            with open("dump", "w") as file: pass
            file.close()
            with open("metadata", "w") as file: pass
            file.close()
            # Non Volatile
            self.cmtlen = 0
            self.current_term = 0
            self.voted_for = None
            self.savemetadata()
        else: # Recovered
            data = self.loadmetadata()
            # Non Volatile
            self.cmtlen   = int(data["cmtlen"])
            self.current_term = int(data["term"])
            self.voted_for = data["votedfor"]
            self.catchup() 
        
        # Volatile
        self.state = "follower"
        self.election_timeout = random.randint(5, 10)
        self.leader_lease_timeout = 5
        self.vote_count = 0
        # self.voted_term = 0
        self.leader_id = None
        self.leader_lease = [0, 0] # time received, duration
        self.leasemap = {}
        self.election_timer = None
        self.leader_lease_timer = None
        self.acklen = {}
        self.sentlen = {}
        self.votesRecieved = set()
        self.reset_election_timer()

    def reset_election_timer(self):
        # Cancel the existing timer if it exists
        if self.election_timer is not None:
            self.election_timer.cancel()
        self.election_timer = threading.Timer(self.election_timeout, self.start_election)
        self.election_timer.start()
        return

    def start_election(self):
        self.state = "candidate"
        self.vote_count = 1
        self.votesRecieved = set()
        print(f"Asking for Votes with term id {self.current_term + 1}")
        self.savedump(f"Node {self.node_id} election timer timed out, Starting election.")
        print(f"Node {self.node_id} election timer timed out, Starting election.")
        self.current_term += 1
        self.voted_for = self.node_id
        self.savemetadata()
        # If Leader is not elected will ask for votes again
        self.reset_election_timer()
        for node_id in range(1, self.total_nodes + 1):
            if node_id == self.node_id: continue
            try:
                self.send_vote_requests(node_id)
            except:
                self.savedump(f"Error occurred while sending RPC to Node {node_id}.")
    
            # Leader already selected no need to send votes anymore
            # if(self.state == "leader"): break
            if(self.state == "follower"): break
    
    def _LastLogIndex(self):
        with open(f"logs_node_{self.node_id}", 'r') as file:
            linecount = sum(1 for line in file if line.strip())
        file.close()
        return linecount - 1
    
    def _LastLogTerm(self):
        with open(f"logs_node_{self.node_id}", 'r') as file:
            idx = self._LastLogIndex()
            lastentry = "0" if idx == -1 else self.getLogentry(idx)
            term = lastentry.split()[-1]
        file.close()
        return int(term)
    
    def AllLeaseAcq(self):
        for lease in self.leasemap:
            if time.perf_counter() < self.leasemap[lease][0] + self.leasemap[lease][1]: return False
        return True
    
    def send_vote_requests(self, node_id):
        # channel = grpc.insecure_channel('localhost:850' + str(node_id))
        channel = grpc.insecure_channel(self.Nodes[node_id][0] + ":" + str(self.Nodes[node_id][1]))
        stub = election_pb2_grpc.ElectionStub(channel)
        response = stub.RequestVote(election_pb2.RequestVoteRequest(term=self.current_term, candidate_id=self.node_id, lastLogIndex=self._LastLogIndex(), lastLogTerm=self._LastLogTerm()))
        channel.close()
        # Need to check log length when term equal
        if response.term > self.current_term:
            # Now a follower
            self.state = "follower"
            # Current term updated to leader's term
            self.voted_for = None
            self.current_term = response.term
            self.savemetadata()
            self.leader_id = node_id
            # Reset timer
            self.reset_election_timer()
            return
    
        if response.vote_granted:
            if node_id not in self.votesRecieved:
                self.vote_count += 1
                self.votesRecieved.add(node_id)
            # Set Previous leader lease
            self.leasemap[node_id] = [time.perf_counter(), response.previousleaderlease]

        if self.vote_count > (self.total_nodes // 2):
            # Reset timer 
            self.reset_election_timer()
            # Waiting for longest lease duration
            while not self.AllLeaseAcq(): continue
            # Start lease timer
            self.start_leader_lease_timer()
            # Now a leader
            self.state = "leader"
            self.leader_id = self.node_id
            logging.info(f"I am the leader with term {self.current_term} and id {self.node_id}")
            self.savedump(f"Node {self.node_id} became the leader for term {self.current_term}.")
            # Append a NO-OP
            self.savelog([f"NO-OP {self.current_term}"])
            self.savedump(f"Node {self.node_id} (leader) appended the entry NO-OP {self.current_term} to the state machine.")
            # Send HeartBeats periodically
            self.HeartBeats()
            return

    def stepdown(self):
        # Need to step down from Leader
        self.state = "follower"
        return
    
    def savelog(self, entries):
        with open(f"logs_node_{self.node_id}", "+a") as file:
            for en in entries:
                file.write(en + "\n")
        file.close()
        return

    def start_leader_lease_timer(self):
        # Cancel the existing timer if it exists
        if self.leader_lease_timer is not None:
            self.leader_lease_timer.cancel()
        
        self.leader_lease_timer = threading.Timer(self.leader_lease_timeout, self.stepdown)
        self.leader_lease_timer.start()
        return

    def HeartBeats(self):
        while(self.state == "leader"):
            start_time = time.perf_counter()
            self.savelog([f"NO-OP {self.current_term}"])
            self.Beat()
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            time.sleep(1 - (elapsed_time))
        return

    def CommitLogEntry(self):
        while self.cmtlen < (self._LastLogIndex() + 1):
            acks = 0
            for node_id in range(1, self.total_nodes + 1):
                if node_id not in self.acklen: self.acklen[node_id] = 0
                if self.acklen[node_id] > self.cmtlen:
                    acks += 1
            
            if acks >= (self.total_nodes // 2):
                self.cmtlen += 1
                self.savemetadata()
            else:
                break

    def Beat(self):
        beats = 1
        beatset = set()
        for node_id in range(1, self.total_nodes + 1):
            if node_id == self.node_id: continue
            try:
                # Updated Here
                if(node_id not in self.sentlen): 
                    self.acklen[node_id] = 0
                    self.sentlen[node_id] = 0
                
                resp = self.ReplicateLogs(node_id)
                if resp.success and (resp.ack >= self.acklen[node_id]):
                    if node_id not in beatset:
                        beats += 1
                        beatset.add(node_id)
                    
                    self.sentlen[node_id] = resp.ack
                    self.acklen[node_id] = resp.ack
                    self.CommitLogEntry()
                elif self.sentlen[node_id] > 0:
                    # No point if isnt called immediately
                    self.sentlen[node_id] = self.sentlen[node_id] - 1
                    # self.ReplicateLogs(node_id)
                elif (resp.term > self.current_term):
                    self.voted_for = None
                    self.current_term = resp.term
                    self.savemetadata()
                    self.state = "follower"
                    self.reset_election_timer()
                
                if(beats > (self.total_nodes // 2)):
                    self.reset_election_timer()
                    while not self.AllLeaseAcq(): continue
                    self.start_leader_lease_timer()
            except: # Couldnot get response
                continue
        
        if(beats <= (self.total_nodes // 2)):
            self.savedump(f"Leader {self.node_id} lease renewal failed. Stepping Down.")

    def catchup(self):
        lst = self.logentries(0)[:self.cmtlen]
        for cmd in lst:
            cmd = cmd.split()
            if cmd[0] == 'SET': self.data[cmd[1]] = int(cmd[2])
        return 

    def logentries(self, start):
        log = None
        with open(f"logs_node_{self.node_id}", 'r') as file:
            log = [line for line in file]
        file.close()
        return log[start:]
    
    def ReplicateLogs(self, node_id):
        channel = grpc.insecure_channel(self.Nodes[node_id][0] + ":" + str(self.Nodes[node_id][1]))
        stub = election_pb2_grpc.ElectionStub(channel)
        # Send heartbeat
        self.savedump(f"Leader {self.node_id} sending heartbeat & Renewing Lease")
        print(f"Leader {self.node_id} sending heartbeat & Renewing Lease")
        prefixLen = self.sentlen[node_id]
        suffix = [] if node_id not in self.sentlen else self.logentries(self.sentlen[node_id])
        prefixTerm = self.Term(self.getLogentry(prefixLen-1)) if prefixLen > 0 else 0
        response = stub.AppendEntries(election_pb2.RequestAppendEntries(term=self.current_term, leaderId=self.node_id, prevLogIndex=prefixLen, prevLogTerm=prefixTerm, leaderCommit=self.cmtlen, entries = suffix, leaseintervalduration=self.leader_lease_timeout))
        channel.close()
        return response
    
    def logOk(self, candidate_LastLogIndex, candidate_LastLogTerm):
        cond1 = candidate_LastLogTerm > self._LastLogTerm()
        return cond1 or (candidate_LastLogTerm == self._LastLogTerm()) and candidate_LastLogIndex >= self._LastLogIndex()
    
    def logOkleader(self, prefixLen, prefixTerm):
        cond1 = (self._LastLogIndex() + 1) >= prefixLen 
        return cond1 and ((prefixLen <= 0) or (self.Term(self.getLogentry(prefixLen-1)) == prefixTerm))
    
    def RequestVote(self, request, context):
        # Voter's response
        if request.term > self.current_term:
            self.state = "follower"
            self.voted_for = None
            self.current_term = request.term
            self.savemetadata()
        if ((self.current_term == request.term) and (self.logOk(request.lastLogIndex, request.lastLogTerm)) and ((self.voted_for == None) or (self.voted_for == request.candidate_id))):
            self.reset_election_timer()
            self.voted_for = request.candidate_id
            self.savemetadata()
            self.savedump(f"Vote granted for Node {request.candidate_id} in term {request.term}.")
            return election_pb2.RequestVoteResponse(term=self.current_term, vote_granted=True, previousleaderlease= max(0, int((self.leader_lease[0] + self.leader_lease[1]) - time.perf_counter())))
        else:
            self.savedump(f"Vote denied for Node {request.candidate_id} in term {request.term}.")
            return election_pb2.RequestVoteResponse(term=self.current_term, vote_granted=False, previousleaderlease= max(0, int((self.leader_lease[0] + self.leader_lease[1]) - time.perf_counter())))
    
    def getLogentry(self, index):
        file_path = f"logs_node_{self.node_id}"
        res = None
        
        with open(file_path, "r") as file:
            lines = file.readlines()
            if (index < len(lines)) and (index >= 0):
                res = lines[index]
        file.close()
        return res
    
    def delete_entries_after_index(self, index):
        file_path = f"logs_node_{self.node_id}"
        updated = 0
        with open(file_path, "r") as file:
            lines = file.readlines()
        file.close()
        if index < len(lines):
            lines = lines[:index + 1]  # Keep entries up to the specified index (inclusive)
            with open(file_path, 'w') as file:
                file.writelines(lines)
                updated = 1
            file.close()
        return updated
    
    def Term(self, log):
        temp = log.strip().split()
        return int(temp[-1])

    def AddToLog(self, prefixlen, leaderCommmit, suffix, id):
        if (len(suffix) > 0) and ((self._LastLogIndex() + 1) > prefixlen):
            index = min(self._LastLogIndex() + 1, prefixlen + len(suffix)) - 1
            if self.Term(self.getLogentry(index)) != self.Term(suffix[index - prefixlen]):
                self.delete_entries_after_index(prefixlen-1)
            
        if (prefixlen + len(suffix)) > (self._LastLogIndex() + 1):
            for i in range ((self._LastLogIndex() + 1) - prefixlen, len(suffix)):
                self.savelog([suffix[i][:-1]])
                self.savedump(f"Node {self.node_id} accepted AppendEntries RPC from {id}.")

        if leaderCommmit > self.cmtlen:
            for i in range(self.cmtlen, leaderCommmit):
                self.savedump(f"Node {self.node_id} (follower) committed the entry {self.getLogentry(i)[:-1]} to the state machine.")
                # continue
            self.cmtlen = leaderCommmit
            self.savemetadata()
        self.catchup()

    
    def AppendEntries(self, request, context):
        # HeartBeat and Append/Commit entry Response
        if(request.term > self.current_term):
            self.current_term = request.term
            self.voted_for = None
            self.savemetadata()
        
        if request.term == self.current_term:
            self.state = "follower"
            self.leader_id = request.leaderId
            self.reset_election_timer()
    
        if((request.term == self.current_term) and (self.logOkleader(request.prevLogIndex, request.prevLogTerm))):
            self.AddToLog(request.prevLogIndex, request.leaderCommit, request.entries, request.leaderId)
            ack = request.prevLogIndex + len(request.entries)
            self.voted_for = request.leaderId
            self.savemetadata()
            # Set request's leader lease
            self.leader_lease = [time.perf_counter(), request.leaseintervalduration]
            return election_pb2.ResponseAppendEntries(term=self.current_term, ack=ack, success=True)
        self.savedump(f"Node {self.node_id} rejected AppendEntries RPC from {self.leader_id}.")
        return election_pb2.ResponseAppendEntries(term=self.current_term, ack=0, success=False)
    
    def ServeClient(self, request, context):
        if self.state == "leader":
            req = request.Request.split()
            if len(req) == 1: # Get request
                if(self.leader_lease_timer != None):
                    K = req[0]
                    reply = ""
                    query = f"GET {K} {self.current_term}"
                    self.savelog([query]) # Append the Entry
                    self.savedump(f"Node {self.node_id} (leader) appended the entry {query} to the state machine.")
                    if K in self.data: reply = str(self.data[K])
                    return election_pb2.ServeClientReply(Data=reply, LeaderID=str(self.leader_id), Success=True)
                else: # No Lease
                    return election_pb2.ServeClientReply(Data="NoLease", LeaderID=str(self.leader_id), Success=False)
            elif len(req) == 2: # Set Request
                K = req[0]
                V = int(req[1])
                query = f"SET {K} {V} {self.current_term}"
                self.savelog([query]) # Append the Entry
                self.savedump(f"Node {self.node_id} (leader) appended the entry {query} to the state machine.")
                snap = self.cmtlen
                self.Beat()
                if((snap + 1) == self.cmtlen):
                    self.savedump(f"Node {self.node_id} (leader) committed the entry {query} to the state machine.")
                    self.data[K] = V
                    return election_pb2.ServeClientReply(Data="", LeaderID=str(self.leader_id), Success=True)
                return election_pb2.ServeClientReply(Data="NotEnoughCommits", LeaderID=str(self.leader_id), Success=False)
            else:
                return election_pb2.ServeClientReply(Data="InvalidRequest", LeaderID=str(self.leader_id), Success=False)
        else:
            if(self.leader_id == None):
                return election_pb2.ServeClientReply(Data="Failure", LeaderID=str(self.leader_id), Success=False)
            else:
                return election_pb2.ServeClientReply(Data="", LeaderID=str(self.leader_id), Success=False)
        
def serve(node, ip_addr, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    election_pb2_grpc.add_ElectionServicer_to_server(node, server)
    server.add_insecure_port(ip_addr + ":" + str(port))
    server.start()
    server.wait_for_termination()

def main():
    if(len(sys.argv) != 4):
        print("Invalid arguments (node.py [nodeid] [ipaddr] [port])")
        return 1
    nodeid, ipaddr, port = sys.argv[1:4]
    random.seed(nodeid)
    node = None
    if(os.path.exists(f"logs_node_{nodeid}")): # Recovery
        print(f"Node with id {nodeid} Recovered!")
        node = Node(int(nodeid), ipaddr, int(port), "recover")
    else: # Initalize
        print(f"Node with id {nodeid} Initalized!")
        node = Node(int(nodeid), ipaddr, int(port), "initalize")
    
    # [::]: port
    serve(node, ipaddr, port)
    return 0

if __name__ == '__main__': main()
