from spyne import Application, rpc, ServiceBase, Integer, Float, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mysqldb import MySQL
from datetime import datetime
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

transferEnvelope : str = lambda account_id_from , account_id_to ,valueToTransfer: f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ban="spyne.bank.soap">
   <soapenv:Header/>
   <soapenv:Body>
      <ban:transfer>
         <ban:from_account_id>{account_id_from}</ban:from_account_id>
         <ban:to_account_id>{account_id_to}</ban:to_account_id>
         <ban:amount>{valueToTransfer}</ban:amount>
      </ban:transfer>
   </soapenv:Body>
</soapenv:Envelope>
"""

withDrawEnvelope  : str = lambda  account_id , valueToWithDraw :f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ban="spyne.bank.soap">
    <soapenv:Header/>
    <soapenv:Body>
        <ban:withdraw>
            <ban:account_id>{account_id}</ban:account_id>
            <ban:amount>{valueToWithDraw}</ban:amount>
        </ban:withdraw>
    </soapenv:Body>
</soapenv:Envelope>
"""

dePositEnvelope  : str = lambda  account_id , valueToDeposit :f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ban="spyne.bank.soap">
    <soapenv:Header/>
    <soapenv:Body>
        <ban:deposit>
            <ban:account_id>{account_id}</ban:account_id>
            <ban:amount>{valueToDeposit}</ban:amount>
        </ban:deposit>
    </soapenv:Body>
</soapenv:Envelope>
"""

    
    


app = Flask(__name__)

CORS(app , supports_credentials = True)

mysql = MySQL(app)

import os

app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST", "localhost")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER", "root")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD", "")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB", "bankdb")

def lookForRows(accountId = 0 , owner_name : str = "" , password : str = ""):
    cur = mysql.connection.cursor()
    cur.execute("SELECT account_id,owner_name , password , balance ,rib FROM accounts WHERE account_id = %s OR( owner_name = %s AND password = %s)",(accountId,owner_name,password))
    rows = cur.fetchall()
  
    if not rows :
        return {"status":"error" , "message" :"User Not Found","Code":404}
    

    columns = [col[0] for col in cur.description] 

    columns.append("status")
    columns.append("message")
    columns.append("Code")

    cur.close()
    
    
    if len(rows) == 1 :
        row = list(rows[0])  
        row.append("success")
        row.append("User Found")
        row.append(200)
        
        return dict(zip(columns,row))
    
    
    return {"status":"error","message": "An error Occured either there is more than one user Or its even broader exception" ,"Code":405}

@app.route('/test' , methods = ['GET'])
def tryOut():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM accounts")
    rows = cur.fetchall()
    

    
    if not rows :
        return jsonify({"message" : "No User in the App"}) , 404

    columns = [col[0] for col in cur.description] 
    columns.append("status")
    columns.append("message")
    columns.append("Code")
    cur.close()
   
    
    result = []

    for row in rows :
        row = list(row) 
        row.append("success")
        row.append("User Found")
        row.append(200)
        result.append(dict(zip(columns,row)))
    
    value :int = int(result[0]['Code'])
    return jsonify(result) , value


    
    






@app.route('/login' , methods = ['POST'])
def logIn():
    data = request.get_json()  
    owner_name = data.get("owner_name","")
    password = data.get("password","")
    accountid = data.get("accountId",0)
    row = lookForRows(accountId=accountid,owner_name=owner_name , password=password)
    value : int = int(row.get("Code",500))
    return jsonify(row) , value

@app.route('/transactions', methods = ['POST'])

def getTransactions()  :
    data = request.get_json()
    owner_name = data.get("owner_name")
    cur  = mysql.connection.cursor()
    cur.execute("SELECT * FROM transactions where from_account_Name = %s OR to_account_Name = %s ",(owner_name,owner_name))
    rows = cur.fetchall()
    columns = [col[0] for col in cur.description] 
    
    
    result = []

    for row in rows :
        row = list(row) 
        result.append(dict(zip(columns,row)))
    print(result)
    return jsonify(result),200    

    



class BankService(ServiceBase):

    @rpc(Integer, Float, _returns=Unicode)
    def deposit(ctx, account_id, amount):
        Deposit : str = 'Deposit'
        try:
            with app.app_context():
                print("Received SOAP deposit:", account_id,"  ", amount)
                data = lookForRows(accountId=account_id)
                if data.get("status") == "error":
                    return "User wasn't found"
                owner_name :str = str(data.get("owner_name"))  
                balance = float(data.get("balance", 0)) + float(amount)
                cur = mysql.connection.cursor()
                cur.execute("UPDATE accounts SET balance=%s WHERE account_id=%s", (balance, account_id))
                cur.execute("INSERT INTO transactions(from_account_Name , type_transaction , to_account_Name , amount) values(%s,%s,%s,%s)",
                    (owner_name,Deposit,owner_name,amount)        )
                mysql.connection.commit()
                cur.close()

                return f"Deposit successful for RIB {data.get('rib','????')}. \n New balance: {balance}"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Internal Error: {str(e)}"

        

    @rpc(Integer, Float, _returns=Unicode)
    def withdraw(ctx, account_id, amount):
        Withdraw : str = 'Withdraw' 
        with app.app_context():
            data = lookForRows(accountId = account_id)
            print(data)
            if data.get("status","No Status") == "No Status":
                return "User wasn't found"
            
            balance : float = float(data.get("balance",0)) - float(amount)

            if balance < 0 :
                return "Can't make this withdrawal  with your  current balance"

            cur = mysql.connection.cursor()
            owner_name :str = str(data.get("owner_name")) 
            cur.execute("UPDATE  accounts SET balance = %s WHERE account_id = %s",(balance,account_id))
            cur.execute("INSERT INTO transactions(from_account_Name , type_transaction , to_account_Name , amount) values(%s,%s,%s,%s)",
                    (owner_name,Withdraw,owner_name,amount)        )

            mysql.connection.commit()

            
            cur.close()
            rib = data.get("rib","????")
            return f"Withdrawal successful for the RIB : {rib}. \n New balance: {balance}."
    
    @rpc(Integer, Integer, Float, _returns=Unicode)
    def transfer(ctx, from_account_id, to_account_id, amount):
        Transfer : str = 'Transfer'
        # 1) Prevent negative or zero transfers
        if amount <= 0:
            return "Amount must be greater than 0."
        with app.app_context():
        # 2) Look up the sender
            sender = lookForRows(accountId=from_account_id)
            if sender.get("Code",404) == 404:
                return "Sender account not found."

            # 3) Look up the receiver
            receiver = lookForRows(accountId=to_account_id)
            if receiver.get("Code",404) == 404:
                return "Receiver account not found."

            sender_balance = float(sender["balance"])
            receiver_balance = float(receiver["balance"])

            # 4) Check sender balance
            if sender_balance < amount:
                return "Insufficient balance."
        
        # 5) Calculate new balances
            new_sender_balance = sender_balance - amount
            new_receiver_balance = receiver_balance + amount

            # 6) DB Update (transaction)
            cur = mysql.connection.cursor()

            try:
                # Deduct from sender
                cur.execute(
                    "UPDATE accounts SET balance=%s WHERE account_id=%s",
                    (new_sender_balance, from_account_id)
                )

                # Add to receiver
                cur.execute(
                    "UPDATE accounts SET balance=%s WHERE account_id=%s",
                    (new_receiver_balance, to_account_id)
                )
                sender_name = sender.get("owner_name")
                receiver_name = receiver.get("owner_name")
                mysql.connection.commit()
                result = (
                    f"Transfer successful.\n"
                    f"From account {sender_name} | new balance: {new_sender_balance}\n"
                    f"To account {receiver_name} | new balance: {new_receiver_balance}"
                )
                cur.execute("INSERT INTO transactions(from_account_Name , type_transaction , to_account_Name , amount) values(%s,%s,%s,%s)",
                    (sender_name,Transfer,receiver_name,amount)        )

            except Exception as e:
                mysql.connection.rollback()
                result = f"Transfer failed: {str(e)}"

            finally:
                cur.close()

            return result


        



soap_app = Application([BankService],
                       tns='spyne.bank.soap',
                       in_protocol=Soap11(validator='lxml'),
                       out_protocol=Soap11())

wsgi_app = WsgiApplication(soap_app)


app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/soap': wsgi_app
})






''''
if __name__ == '__main__':

    app.run(debug = True , host = '0.0.0.0' , port = 5000)'''
    
