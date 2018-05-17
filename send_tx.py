import sys
import cbor
import string
import random
from urllib.error import HTTPError
from random import randint
import urllib.request

from hashlib import sha512

from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
import sawtooth_sdk
from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch
from sawtooth_sdk.protobuf.batch_pb2 import BatchList

#Creates a signer who will sign the tx and validate
#its identity in front of the validator
context = create_context('secp256k1')
private_key = context.new_random_private_key()

signer = CryptoFactory(context).new_signer(private_key)
print("SIGNER ES: {}".format(signer.get_public_key().as_hex()))

#Checks for correct amount of parameters
if len(sys.argv) != 3:
	print("Use: ./send_tx NumOfBatches NumOfTxPerBatch")
	sys.exit(1)

NUM_BATCHES = int(sys.argv[1])
NUM_TX_PER_BATCH = int(sys.argv[2])

#Generate the payload of the tx
#Every family has a structure to follow
#Uses the cbor format

N = 10

ran_addr = [
	[
	''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))
	for j in range(NUM_TX_PER_BATCH)
	] for i in range(NUM_BATCHES)	
]

payload_arr = [
	[{
		'Verb': 'set',
		'Name': ran_addr[i][j],
		'Value': randint(0, 30000)
	 } for j in range(NUM_TX_PER_BATCH)
	] for i in range(NUM_BATCHES)
]

#Generate the bytes of the payload
payload_bytes_arr = [
	[
	cbor.dumps(payload_arr[i][j])
	for j in range(NUM_TX_PER_BATCH)
	] for i in range(NUM_BATCHES)
]
 
#Generate an integerkey address holding 'example'
tx_addr = [
	[
	sha512('intkey'.encode('utf-8')).hexdigest()[0:6] + sha512(ran_addr[i][j].encode('utf-8')).hexdigest()[-64:]
	for j in range(NUM_TX_PER_BATCH)
	] for i in range(NUM_BATCHES) 
]
print("LA DIRECCION ES: {}".format(tx_addr))

#Generate the tx header
tx_header_arr = [
	[	
		TransactionHeader(
			family_name='intkey',
			family_version='1.0',
			inputs=[tx_addr[i][j]],
			outputs=[tx_addr[i][j]],
			signer_public_key = signer.get_public_key().as_hex(),
			batcher_public_key = signer.get_public_key().as_hex(),
			dependencies=[],
			payload_sha512 = sha512(payload_bytes_arr[i][j]).hexdigest()
		).SerializeToString()
	for j in range(NUM_TX_PER_BATCH)
	] for i in range(NUM_BATCHES)
]

#Signer signs the header:
signature_arr = [
	[
		signer.sign(tx_header_arr[i][j])
	for j in range(NUM_TX_PER_BATCH)
	] for i in range(NUM_BATCHES)
]

#Generate an array with all the transactions
tx_arr= [
		[Transaction(
			header=tx_header_arr[i][j],
			header_signature=signature_arr[i][j],
			payload = payload_bytes_arr[i][j]
			)
		for j in range(NUM_TX_PER_BATCH)
		]
	for i in range(NUM_BATCHES)
	]

#Create the BatchHeader
batch_header_arr = [
	BatchHeader(
		signer_public_key = signer.get_public_key().as_hex(),
		transaction_ids = [
			tx_arr[i][j].header_signature
		for j in range(NUM_TX_PER_BATCH)
		]
	).SerializeToString()
	for i in range(NUM_BATCHES)
]

#Create the batch with the tx
signature_batch_arr = [signer.sign(batch_header_arr[i]) for i in range(NUM_BATCHES)]

batch_arr = [
	Batch(
		header = batch_header_arr[i],
		header_signature = signature_batch_arr[i],
		transactions = tx_arr[i]
	) for i in range(NUM_BATCHES)]

#Collect all Batches in a BatchList: can contain batches from different clients
batch_list_arr = [
	BatchList(
		batches = [batch_arr[i]]
	).SerializeToString()
	for i in range(NUM_BATCHES)
]

#Send Batches to Validator
try:
	request_arr = [
		urllib.request.Request(
			'http://rest-api:8008/batches',
			batch_list_arr[i],
			method = 'POST',
			headers = {'Content-Type': 'application/octet-stream'}
		)
	for i in range(NUM_BATCHES)]

	response_arr = [urllib.request.urlopen(request_arr[i]) for i in range(NUM_BATCHES)]

except HTTPError as e:
	response = e.file

print(payload_arr);
