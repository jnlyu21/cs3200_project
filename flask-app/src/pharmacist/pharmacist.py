
# import statements
import random
from flask import Blueprint, request, jsonify, make_response, current_app
import json
from src import db


pharmacist = Blueprint('pharmacist', __name__)

#display all prescriptions for a specific branch
@pharmacist.route('/prescriptions/<int:pharmacy_id>/<int:branch_id>', methods=['GET'])
def get_prescriptions(pharmacy_id, branch_id):
    try:
        cursor = db.get_db().cursor()
        query = f'SELECT PrescriptionID, PatientID, DrugID, Status FROM Prescription WHERE PharmacyID = "{pharmacy_id}" AND BranchID = "{branch_id}"'
        cursor.execute(query)
        results = cursor.fetchall()

        prescriptions = [
            {
                'Prescription ID': result[0],
                'Patient ID': result[1],
                'Drug ID': result[2],
                'Status': result[3],
            } for result in results
        ]
        return jsonify(prescriptions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Display information of all pharmacists
@pharmacist.route('/pharmacist', methods=['GET'])
def get_all_pharmacists():
    try:
        cursor = db.get_db().cursor()
        cursor.execute(
            "SELECT PharmacistID, BranchID, PharmacyID, FirstName, LastName FROM Pharmacist"
        )

        row_headers = [x[0] for x in cursor.description]
        json_data = []
        results = cursor.fetchall()
        for result in results:
            json_data.append(dict(zip(row_headers, result)))

        response = make_response(jsonify(json_data), 200)
        response.mimetype = 'application/json'
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
# Allow pharmacist to change prescription status to complete
@pharmacist.route('/prescriptions/<int:prescription_id>', methods=['PUT'])
def complete_prescription(prescription_id):
    try:
        # Check if the prescription is currently active
        cursor = db.get_db().cursor()
        status_check_query = f'SELECT Status FROM Prescription WHERE PrescriptionID = "{prescription_id}"'
        cursor.execute(status_check_query)
        current_status = cursor.fetchone()
        if not current_status:
            return 'Prescription not found.', 404
        if current_status[0] != 'Active':
            return 'Prescription is not Active, cannot be completed.', 400

        # Update the prescription status to 'Complete'
        update_query = f'UPDATE Prescription SET Status = "Complete" WHERE PrescriptionID = "{prescription_id}"'
        cursor.execute(update_query)
        db.get_db().commit()
        return 'status successfully updated', 200
    except Exception as e:
        db.get_db().rollback()
        return str(e), 500
    
#Allow pharmacist to view all stock of a specific branch joining with medication table
@pharmacist.route('/stock/<int:pharmacy_id>/<int:branch_id>', methods=['GET'])
def get_stock(pharmacy_id, branch_id):
    try:
        cursor = db.get_db().cursor()
        query = f'SELECT Stock_Item.DrugID, Quantity, SKU, Name FROM Stock_Item JOIN Medication ON Stock_Item.DrugID = Medication.DrugID WHERE PharmacyID = "{pharmacy_id}" AND BranchID = "{branch_id}"'
        cursor.execute(query)
        results = cursor.fetchall()

        stock = [
            {
                'Drug ID': result[0],
                'Quantity': result[1],
                'SKU': result[2],
                'Name': result[3]
            } for result in results
        ]
        return jsonify(stock), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# When a pharmacist fulfills an order, the quantity of the drug must be deducted from the branch's stock
@pharmacist.route('/stock/<int:pharmacy_id>/<int:branch_id>/<int:drug_id>', methods=['PUT'])
def deduct_drug_stock(pharmacy_id, branch_id, drug_id):
    try:
        the_data = request.json
        used_quantity = the_data['used_quantity']

        cursor = db.get_db().cursor()
        
        # Check there sufficient stock of drug
        check_query = f'SELECT Quantity FROM Stock_Item WHERE PharmacyID = "{pharmacy_id}" AND BranchID = "{branch_id}" AND DrugID = "{drug_id}"'
        cursor.execute(check_query)
        result = cursor.fetchone()
        if not result:
            return jsonify({'message': 'Drug not in this branch'})
        current_quantity = result[0]

        if current_quantity < used_quantity:
            return jsonify({'message': 'We do not have sufficient quantity of the medication to fulfill this order'})
        
        new_quantity = current_quantity - used_quantity
        update_query = f'UPDATE Stock_Item SET Quantity = "{new_quantity}" WHERE PharmacyID = "{pharmacy_id}" AND BranchID = "{branch_id}" AND DrugID = "{drug_id}"'
        cursor.execute(update_query)
        db.get_db.commit()

        return jsonify({'message': 'Stock updated successfully.', 'New Quantity': new_quantity}), 200
    except Exception as e:
        db.get_db().rollback()
        return jsonify({"error": str(e)}), 500
    
    # Add pharmacist
@pharmacist.route('/pharmacist/<int:admin_id>', methods=['POST'])
def add_pharmacist():
    try:
        # Collecting data 
        the_data = request.json
        branch_id = the_data['branch_id']
        pharmacy_id = the_data['pharmacy_id']
        first_name = the_data['first_name']
        last_name = the_data['last_name']

        # Construct query
        query = 'INSERT INTO Pharmacist (BranchID, PharmacyID, FirstName, LastName) VALUES ('
        query += f'"{branch_id}", "{pharmacy_id}", "{first_name}", "{last_name}")'

        # Execute
        cursor = db.get_db().cursor()
        cursor.execute(query)
        db.get_db().commit()
        return 'Pharmacist added successfully!', 201

    except Exception as e:
        db.get_db().rollback()
        return jsonify({"error": str(e)}), 500
    

#View the specific prescription ID
@pharmacist.route('/prescriptions/<int:prescription_id>', methods=['GET'])
def view_prescription(prescription_id):
    try:
        cursor = db.get_db().cursor()
        query = f'SELECT * FROM Prescription WHERE PrescriptionID = "{prescription_id}"'
        cursor.execute(query)
        prescription = cursor.fetchone()

        if prescription:
            prescription_data = {
                'Prescription ID': prescription[0],
                'Prescribed By': prescription[1],
                'Patient ID': prescription[2],
                'Pharmacy ID': prescription[3],
                'Branch ID': prescription[4],
                'Dosage': prescription[5],
                'Status': prescription[6],
                'Prescribed Date': prescription[7].strftime('%Y-%m-%d'),
                'Prescribed Expiration': prescription[8].strftime('%Y-%m-%d'),
                'Drug ID': prescription[9]
            }
            return jsonify(prescription_data), 200
        else:
            return jsonify({"error": "Prescription not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#check medication name given drug id
@pharmacist.route('/medication/<int:drug_id>', methods=['GET'])
def get_drug_name(drug_id):
    try:
        cursor = db.get_db().cursor()
        query = f'SELECT Name FROM Medication WHERE DrugID = "{drug_id}"'
        cursor.execute(query)
        result = cursor.fetchone()

        if not result:
            return jsonify({'message': 'Drug not found'}), 404
        drug_name = result[0]
        return jsonify({'Drug ID': drug_id, 'Drug Name': drug_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#get all prescriptions
@pharmacist.route('/prescriptions/all', methods=['GET'])
def get_all_prescriptions():
    try:
        cursor = db.get_db().cursor()
        cursor.execute(
            "SELECT * FROM Prescription"
        )

        row_headers = [x[0] for x in cursor.description]
        json_data = []
        results = cursor.fetchall()
        for result in results:
            json_data.append(dict(zip(row_headers, result)))

        response = make_response(jsonify(json_data), 200)
        response.mimetype = 'application/json'
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#allow pharmacist to create a new order
@pharmacist.route('/stock/<int:pharmacy_id>/<int:branch_id>/<int:drug_id>', methods=['POST'])
def create_order(pharmacy_id, branch_id, drug_id):
    try:
        the_data = request.json
        quantity = the_data['quantity']

        cursor = db.get_db().cursor()
        
        # Check if the drug is already in stock
        check_query = f'SELECT Quantity FROM Stock_Item WHERE PharmacyID = "{pharmacy_id}" AND BranchID = "{branch_id}" AND DrugID = "{drug_id}"'
        cursor.execute(check_query)
        result = cursor.fetchone()

        if result:
            # Drug is already in stock, add the quantity to the current quantity
            current_quantity = result[0]
            new_quantity = current_quantity + quantity
            update_query = f'UPDATE Stock_Item SET Quantity = "{new_quantity}" WHERE PharmacyID = "{pharmacy_id}" AND BranchID = "{branch_id}" AND DrugID = "{drug_id}"'
            cursor.execute(update_query)
            db.get_db().commit()
            return jsonify({'message': 'Order successfully added to stock.', 'New Quantity': new_quantity}), 200
        else:
            # Drug is not in stock, add it to stock
            sku = random.randint(100000, 999999)
            insert_query = f'INSERT INTO Stock_Item (PharmacyID, BranchID, DrugID, Quantity, SKU) VALUES ("{pharmacy_id}", "{branch_id}", "{drug_id}", "{quantity}", "{sku}")'
            cursor.execute(insert_query)
            db.get_db().commit()
            return jsonify({'message': 'Order successfully added to stock.'}), 200
    except Exception as e:
        db.get_db().rollback()
        return jsonify({"error": str(e)}), 500


# TODO: allow pharmacist to make an order, add quantity to current drug's quantity. If drug is not in Stock_Item table for branch, add it and make a new randomly generated SKU (unique)