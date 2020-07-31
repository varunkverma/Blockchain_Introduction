# module 2 - create a Cryptocurrency
 
# importing the libraries
import datetime
import hashlib
import json
from flask import Flask,jsonify,request
import requests
from uuid import uuid4
from urllib.parse import urlparse

# Part 1 - Building a Blockchain

class Blockchain:
    
    def __init__(self):
        # chain in which blocks will be added
        self.chain=[]
        # temp list of transactions before they are added to a mined block
        self.transactions=[]
        # initialising the first block
        self.create_block(proof=1, previous_hash="0")
        # nodes participating in the distributing system
        self.nodes=set()
    
    def create_block(self,proof,previous_hash):
        # structure of a block
        block={
                "index":len(self.chain)+1,
                "timestamp":str(datetime.datetime.now()),
                "proof":proof,
                "previous_hash":previous_hash,
                "transactions":self.transactions
            }
        # transactions are added to the block, so empty the temp transactions list
        self.transactions=[]
        # adding the block to the chain
        self.chain.append(block)
        return block
    
    def get_previous_block(self):
        return self.chain[-1]
    
    def proof_of_work(self,previous_proof):
        # finding the nonce, through brute force
        new_proof=1
        check_proof=False
        while check_proof is False:
            puzzle=new_proof**2 - previous_proof**2
            hash_operation = hashlib.sha256(str(puzzle).encode()).hexdigest()
            if(hash_operation[:4]=="0000"):
                check_proof=True
            else:
                new_proof+=1
        return new_proof
    
    def hash(self,block):
        # To get the hash of the block
        encoded_block=json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self,chain):
        previous_block=chain[0] # Genesis block
        block_index=1
        while block_index<len(chain):
            # Get the current block
            block=chain[block_index]
            
            # check if the previous hash of the current block doesn't match the hash of the previous block, return False
            if(block["previous_hash"]!=self.hash(previous_block)):
                return False
            
            # check if the current block's nonce/proof is valid
            proof=block["proof"]
            previous_proof=previous_block["proof"]
            puzzle=proof**2 - previous_proof**2
            hash_operation = hashlib.sha256(str(puzzle).encode()).hexdigest()
            if(hash_operation[:4]!="0000"):
                return False
            
            # make current block as the previous block for the next iteration
            previous_block=block
            
            # increment the value of block_index
            block_index+=1
        return True
    
    def add_transaction(self,sender,receiver,amount):
        # appending a new transaction object to the list of transactions
        self.transactions.append({
            "sender":sender,
            "receiver":receiver,
            "amount":amount
            })        
        # returning the index of the next block in which transactions need to be added
        previous_block=self.get_previous_block()
        return previous_block["index"]+1
    
    def add_node(self,address):
        # parse the url to get the parsed address
        parsed_url=urlparse(address)
        # adding the parsed url to the set of nodes
        self.nodes.add(parsed_url.netloc)
         
    # establishing consesus
    def replace_chain(self):
        # network i.e., all the nodes
        network=self.nodes
        
        # initializing the longest chain
        longest_chain=None
        
        # initializing the max length of the longest chain with the value of the current Node's blockchain's length
        max_length=len(self.chain)
        
        # iterating over the nodes
        for node in network:
            # GET request to get the blockchain of the node
            response=requests.get(f"http://{node}/get_chain")
            node_blockchain=response.json()
            # check if the response was 200(success) and
            #if the length of the node's blockchain > max_length and if the node's blockchain is valid
            if response.status_code == 200 and node_blockchain["length"] > max_length and self.is_chain_valid(node_blockchain["chain"]):
                max_length=node_blockchain["length"]
                longest_chain=node_blockchain["chain"]
            
        if longest_chain:
            # replace the chain
            self.chain=longest_chain
            return True
        # no replacement made, i.e., the current node's chain is the longest chain
        return False
        
        
# Part 2 - Mining our blockchain

# Creating a web app
app=Flask(__name__)        
        
# Creating an address for the node on PORT: 5000
node_address=str(uuid4()).replace("-", "")

# Creating a blockchain
blockchain=Blockchain()

# mining a new block
@app.route("/mine_block",methods=["GET"])
def mine_block():
    # Get the last block as we need its proof/nonce
    previous_block=blockchain.get_previous_block()
    previous_proof=previous_block["proof"];
    
    # Get the proof/nonce
    proof=blockchain.proof_of_work(previous_proof)
    
    # Get the previous_hash
    previous_hash=blockchain.hash(previous_block)
    
    # add the transaction to the blockchain's temp transaction list
    # first transaction to pay the miner for mining the block, who is assumed to have mined a block for the node with address node_address
    blockchain.add_transaction(sender=node_address, receiver="You", amount=1)
    
    # Create the new block and add it to the chain
    block=blockchain.create_block(proof, previous_hash)
    
    response={
        **block,
        "message":"Congrats, you just mined a block!",
        }
    
    return jsonify(response), 200

# Get the full Blockchain
@app.route("/get_chain",methods=["GET"])
def get_chain():
    response={
            "chain": blockchain.chain,
            "length":len(blockchain.chain)
        }
    return jsonify(response), 200

# Get a check result if Blockchain is still valid
@app.route("/is_valid",methods=["GET"])
def is_valid():
    is_valid=blockchain.is_chain_valid(blockchain.chain)
    response={"message":"The Blockchain is NOT valid anymore."}
    if is_valid:
        response={"message":"The Blockchain is valid."}
    return jsonify(response), 200

# Add a new transaction to the Blockchain
@app.route("/add_transaction",methods=["POST"])
def add_transaction():
    # Get the json object send over the POST request's body
    json = request.get_json()
    # The fields necessary to be a part of add_transaction's POST request's body object
    transaction_keys=['sender','receiver','amount']
    # Check if all the keys are present
    if not all(key in json for key in transaction_keys):
        # return a Bad Request as response
        return "Some elements of the transaction are missing", 400
    # Add transaction to the Blockchain
    index=blockchain.add_transaction(sender=json["sender"], receiver=json["receiver"], amount=json["amount"])
    # Create the response
    response = {
            "message":f"This transaction will be added to Block {index}"
        }
    # Return the response
    return jsonify(response), 201

# Part 3 - Decentralizing our Blockchain

# Connecting new nodes
@app.route("/connect_node",methods=["POST"])
def connect_node():
    # Get the POST request's body
    json=request.get_json()
    # Extract the nodes from the body object
    nodes=json.get("nodes")
    # checking if nodes are missing
    if nodes is None:
        return "No node", 400
    # iterate over each node 
    for node in nodes:
        # adding the node to the blockchain list of nodes
        blockchain.add_node(node)
    # Creating the response
    response={
        "message":"All the nodes are now connected. The Hadcoin Blockchain now contains the nodes:",
        "total_nodes":list(blockchain.nodes)
        }    
    return jsonify(response), 201

# Replacing the chain by the longest chain if needed
@app.route("/replace_chain",methods=["GET"])
def replace_chain():
    # call the blockchain's method to verify and if required the longest chain
    is_chain_replaced=blockchain.replace_chain()
    
    response={}
    
    # if is_chain_replaced is True then the blockchain's chain has been replaced with the longest chain among the nodes
    if is_chain_replaced:
        response={
            "message":"The nodes had different chain so the chain were replaced by the longest chain",
            "new_chain":blockchain.chain
            }
    else:
        response={
            "message":"All good, the chain is the longest chain",
            "actual_chain":blockchain.chain
            }
    return jsonify(response), 200
# Running the app
app.run(host="0.0.0.0",port=5003)