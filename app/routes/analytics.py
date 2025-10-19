from flask import Blueprint, request, jsonify
from app.models.database import create_connection
from mysql.connector import Error
from collections import Counter
import json
from app.utils.tokenCheck import token_required

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/compensation/overallStats', methods=['POST'])
@token_required
def get_overall_compensation_stats(decoded_data):
    data = request.json
    emp_id = data.get('emp_id')
    token_emp = decoded_data.get('employee', {})
    roll = token_emp.get('roll')
    if not emp_id:
        return jsonify({"error": "Missing required field: emp_id"}), 400

    if (str(decoded_data.get("emp_id")) != str(emp_id) and (roll!="ccf" or roll!="pccf") ):
        return jsonify({"error": "Unauthorized access"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT 
              SUM(totalCompensationAmount) AS total_compensation,
              AVG(totalCompensationAmount) AS avg_compensation,
              COUNT(*) AS total_forms,

              SUM(CASE WHEN cropdamageAmount > 0 THEN cropdamageAmount ELSE 0 END) AS total_crop_damage,
              SUM(CASE WHEN houseDamageAmount > 0 THEN houseDamageAmount ELSE 0 END) AS total_house_damage,
              SUM(CASE WHEN catleInjuryAmount > 0 THEN catleInjuryAmount ELSE 0 END) AS total_cattle_injury,
              SUM(CASE WHEN humanInjuryAmount > 0 THEN humanInjuryAmount ELSE 0 END) AS total_human_injury,
              SUM(CASE WHEN humanDeathAmount > 0 THEN humanDeathAmount ELSE 0 END) AS total_human_death,

              SUM(CASE WHEN cropdamageAmount > 0 THEN 1 ELSE 0 END) AS crop_damage_forms,
              SUM(CASE WHEN houseDamageAmount > 0 THEN 1 ELSE 0 END) AS house_damage_forms,
              SUM(CASE WHEN catleInjuryAmount > 0 THEN 1 ELSE 0 END) AS cattle_injury_forms,
              SUM(CASE WHEN humanInjuryAmount > 0 THEN 1 ELSE 0 END) AS human_injury_forms,
              SUM(CASE WHEN humanDeathAmount > 0 THEN 1 ELSE 0 END) AS human_death_forms,

              SUM(CASE WHEN Status IN ('1', '2', '3', '4', '5') THEN 1 ELSE 0 END) AS pending_forms,
              SUM(CASE WHEN Status = '6' THEN 1 ELSE 0 END) AS accepted_forms,
              SUM(CASE WHEN Status = '-1' THEN 1 ELSE 0 END) AS rejected_forms,

              -- Animal-wise counts
              SUM(CASE WHEN AnimalName = 'Elephant (हाथी)' THEN 1 ELSE 0 END) AS elephant_count,
              SUM(CASE WHEN AnimalName = 'Leopard (तेंदुआ)' THEN 1 ELSE 0 END) AS leopard_count,
              SUM(CASE WHEN AnimalName = 'Tiger (बाघ)' THEN 1 ELSE 0 END) AS tiger_count,
              SUM(CASE WHEN AnimalName = 'Sloth Bear (कंबल भालू)' THEN 1 ELSE 0 END) AS sloth_bear_count,
              SUM(CASE WHEN AnimalName = 'Hyena (हाइना)' THEN 1 ELSE 0 END) AS hyena_count,
              SUM(CASE WHEN AnimalName = 'Wild Boar (जंगली सूअर)' THEN 1 ELSE 0 END) AS wild_boar_count,
              SUM(CASE WHEN AnimalName = 'Jungle Cat (जंगल बिल्ली)' THEN 1 ELSE 0 END) AS jungle_cat_count

            FROM compensationform;
        """
        cursor.execute(query)
        stats = cursor.fetchone()

        if not stats:
            return jsonify({"message": "No data found"}), 404

        return jsonify({
            "totalCompensationAmount": round(stats['total_compensation'] or 0, 2),
            "averageCompensationAmount": round(stats['avg_compensation'] or 0, 2),
            "totalForms": stats['total_forms'] or 0,
            "statusWiseCounts":{
                "totalPendingForms": int(stats['pending_forms'] or 0),
                "totalAcceptedForms": int(stats['accepted_forms'] or 0),
                "totalRejectedForms": int(stats['rejected_forms'] or 0),

            },
            "damageWiseCounts":{
                "cattleInjuryForms": int(stats['cattle_injury_forms'] or 0),
                "cropDamageForms": int(stats['crop_damage_forms'] or 0),
                "houseDamageForms": int(stats['house_damage_forms'] or 0),
                "humanDeathForms": int(stats['human_death_forms'] or 0),
                "humanInjuryForms": int(stats['human_injury_forms'] or 0),

            },
            "damageWiseAmounts":{
                "totalCropDamageAmount": round(stats['total_crop_damage'] or 0, 2),
                "totalHouseDamageAmount": round(stats['total_house_damage'] or 0, 2),
                "totalCattleInjuryAmount": round(stats['total_cattle_injury'] or 0, 2),
                "totalHumanInjuryAmount": round(stats['total_human_injury'] or 0, 2),
                "totalHumanDeathAmount": round(stats['total_human_death'] or 0, 2),
                
            },
            "animalWiseCounts": {
                "Elephant (हाथी)": stats['elephant_count'],
                "Leopard (तेंदुआ)": stats['leopard_count'],
                "Tiger (बाघ)": stats['tiger_count'],
                "Sloth Bear (कंबल भालू)": stats['sloth_bear_count'],
                "Hyena (हाइना)": stats['hyena_count'],
                "Wild Boar (जंगली सूअर)": stats['wild_boar_count'],
                "Jungle Cat (जंगल बिल्ली)": stats['jungle_cat_count'],
            }
        }),200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@analytics_bp.route('/compensation/circleStats', methods=['POST'])
@token_required
def get_compensation_circle_stats(decoded_data):
    data = request.json
    circle = data.get('circle')
    emp_id = data.get('emp_id')
    token_emp = decoded_data.get('employee', {})
    roll = token_emp.get('roll')
    if not circle or not emp_id:
        return jsonify({"error": "Missing required field: circle or emp_id"}), 400
    if (str(decoded_data.get("emp_id")) != str(emp_id) and (roll!="ccf" or roll!="pccf") ):
        return jsonify({"error": "Unauthorized access"}), 403


    connection = create_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. Fetch stats
        stats_query = """
            SELECT 
                SUM(totalCompensationAmount) AS total_compensation,
                AVG(totalCompensationAmount) AS avg_compensation,
                COUNT(*) AS total_forms,

                SUM(CASE WHEN cropdamageAmount > 0 THEN cropdamageAmount ELSE 0 END) AS total_crop_damage,
                SUM(CASE WHEN houseDamageAmount > 0 THEN houseDamageAmount ELSE 0 END) AS total_house_damage,
                SUM(CASE WHEN catleInjuryAmount > 0 THEN catleInjuryAmount ELSE 0 END) AS total_cattle_injury,
                SUM(CASE WHEN humanInjuryAmount > 0 THEN humanInjuryAmount ELSE 0 END) AS total_human_injury,
                SUM(CASE WHEN humanDeathAmount > 0 THEN humanDeathAmount ELSE 0 END) AS total_human_death,

                SUM(CASE WHEN cropdamageAmount > 0 THEN 1 ELSE 0 END) AS crop_damage_forms,
                SUM(CASE WHEN houseDamageAmount > 0 THEN 1 ELSE 0 END) AS house_damage_forms,
                SUM(CASE WHEN catleInjuryAmount > 0 THEN 1 ELSE 0 END) AS cattle_injury_forms,
                SUM(CASE WHEN humanInjuryAmount > 0 THEN 1 ELSE 0 END) AS human_injury_forms,
                SUM(CASE WHEN humanDeathAmount > 0 THEN 1 ELSE 0 END) AS human_death_forms,

                SUM(CASE WHEN Status IN ('1', '2', '3', '4', '5') THEN 1 ELSE 0 END) AS pending_forms,
                SUM(CASE WHEN Status = '6' THEN 1 ELSE 0 END) AS accepted_forms,
                SUM(CASE WHEN Status = '-1' THEN 1 ELSE 0 END) AS rejected_forms,

                -- Animal wise
                SUM(CASE WHEN AnimalName = 'Elephant (हाथी)' THEN 1 ELSE 0 END) AS elephant_count,
                SUM(CASE WHEN AnimalName = 'Leopard (तेंदुआ)' THEN 1 ELSE 0 END) AS leopard_count,
                SUM(CASE WHEN AnimalName = 'Tiger (बाघ)' THEN 1 ELSE 0 END) AS tiger_count,
                SUM(CASE WHEN AnimalName = 'Sloth Bear (कंबल भालू)' THEN 1 ELSE 0 END) AS sloth_bear_count,
                SUM(CASE WHEN AnimalName = 'Hyena (हाइना)' THEN 1 ELSE 0 END) AS hyena_count,
                SUM(CASE WHEN AnimalName = 'Wild Boar (जंगली सूअर)' THEN 1 ELSE 0 END) AS wild_boar_count,
                SUM(CASE WHEN AnimalName = 'Jungle Cat (जंगल बिल्ली)' THEN 1 ELSE 0 END) AS jungle_cat_count
            FROM compensationform
            WHERE Circle_CG = %s
        """
        cursor.execute(stats_query, (circle,))
        stats = cursor.fetchone()

        if not stats or stats['total_forms'] == 0:
            return jsonify({"message": "No data found for this circle"}), 404

        # 2. Fetch all forms
        forms_query = """
            SELECT FormID, SubmissionDateTime,ForestGuardID, complaint_id, ApplicantName, Mobile, IncidentDate,Circle_CG, Circle1,division,subdivision,range_,beat,statusHistory, AnimalName,totalCompensationAmount,lat,longitude
            FROM compensationform
            WHERE Circle_CG = %s
        """
        cursor.execute(forms_query, (circle,))
        forms_records = cursor.fetchall()

        forms_list = []
        animal_names = []

        for form in forms_records:
            try:
                status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
            except json.JSONDecodeError:
                status_history = []

            forms_list.append({
                "formID": form["FormID"],
                "forestGuardID": form["ForestGuardID"],
                "submissionDateTime":form["SubmissionDateTime"],
                "totalCompensationAmount": form["totalCompensationAmount"],
                "complaint_id": form["complaint_id"],
                "applicantName": form["ApplicantName"],
                "mobile": form["Mobile"],
                "incidentDate": form["IncidentDate"],
                "circle_CG": form["Circle_CG"],
                "circle1": form["Circle1"],
                "division": form["division"],
                "subdivision": form["subdivision"],
                "range_": form["range_"],
                "beat": form["beat"],
                "statusHistory": status_history,
                "AnimalName":form["AnimalName"],
                "lat":form["lat"],
                "long":form["longitude"]
            })

            if form.get("AnimalName"):
                animal_names.append(form["AnimalName"])

        # Find most frequent animal
        most_common_animal = Counter(animal_names).most_common(1)
        top_animal = most_common_animal[0][0] if most_common_animal else None

        return jsonify({
            "totalCompensationAmount": round(stats['total_compensation'] or 0, 2),
            "averageCompensationAmount": round(stats['avg_compensation'] or 0, 2),
            "totalForms": stats['total_forms'] or 0,

            "mostFrequentAnimal": top_animal,

            "statusWiseCounts":{
                "totalPendingForms": int(stats['pending_forms'] or 0),
                "totalAcceptedForms": int(stats['accepted_forms'] or 0),
                "totalRejectedForms": int(stats['rejected_forms'] or 0),

            },
            "damageWiseCounts":{
                "cattleInjuryForms": int(stats['cattle_injury_forms'] or 0),
                "cropDamageForms": int(stats['crop_damage_forms'] or 0),
                "houseDamageForms": int(stats['house_damage_forms'] or 0),
                "humanDeathForms": int(stats['human_death_forms'] or 0),
                "humanInjuryForms": int(stats['human_injury_forms'] or 0),

            },
            "damageWiseAmounts":{
                "totalCropDamageAmount": round(stats['total_crop_damage'] or 0, 2),
                "totalHouseDamageAmount": round(stats['total_house_damage'] or 0, 2),
                "totalCattleInjuryAmount": round(stats['total_cattle_injury'] or 0, 2),
                "totalHumanInjuryAmount": round(stats['total_human_injury'] or 0, 2),
                "totalHumanDeathAmount": round(stats['total_human_death'] or 0, 2),
                
            },
            "animalWiseCounts": {
                "Elephant (हाथी)": stats['elephant_count'],
                "Leopard (तेंदुआ)": stats['leopard_count'],
                "Tiger (बाघ)": stats['tiger_count'],
                "Sloth Bear (कंबल भालू)": stats['sloth_bear_count'],
                "Hyena (हाइना)": stats['hyena_count'],
                "Wild Boar (जंगली सूअर)": stats['wild_boar_count'],
                "Jungle Cat (जंगल बिल्ली)": stats['jungle_cat_count'],
            },
            "forms": forms_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@analytics_bp.route('/compensation/divisionStats', methods=['POST'])
@token_required
def get_division_compensation_stats(decoded_data):
    data = request.json
    emp_id = data.get('emp_id')
    circle = data.get('circle')
    division = data.get('division')
    token_emp = decoded_data.get('employee', {})
    roll = token_emp.get('roll')
    if not circle or not division or not emp_id:
        return jsonify({"error": "Missing required field: circle or division or empId"}), 400

    if (str(decoded_data.get("emp_id")) != str(emp_id) and (roll!="ccf" or roll!="pccf") ):
        return jsonify({"error": "Unauthorized access"}), 403


    connection = create_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. Stats query
        stats_query = """
            SELECT
                SUM(totalCompensationAmount) AS total_compensation,
                AVG(totalCompensationAmount) AS avg_compensation,
                COUNT(*) AS total_forms,
                SUM(CASE WHEN cropdamageAmount > 0 THEN cropdamageAmount ELSE 0 END) AS total_crop_damage,
                SUM(CASE WHEN houseDamageAmount > 0 THEN houseDamageAmount ELSE 0 END) AS total_house_damage,
                SUM(CASE WHEN catleInjuryAmount > 0 THEN catleInjuryAmount ELSE 0 END) AS total_cattle_injury,
                SUM(CASE WHEN humanInjuryAmount > 0 THEN humanInjuryAmount ELSE 0 END) AS total_human_injury,
                SUM(CASE WHEN humanDeathAmount > 0 THEN humanDeathAmount ELSE 0 END) AS total_human_death,
                SUM(CASE WHEN cropdamageAmount > 0 THEN 1 ELSE 0 END) AS crop_damage_forms,
                SUM(CASE WHEN houseDamageAmount > 0 THEN 1 ELSE 0 END) AS house_damage_forms,
                SUM(CASE WHEN catleInjuryAmount > 0 THEN 1 ELSE 0 END) AS cattle_injury_forms,
                SUM(CASE WHEN humanInjuryAmount > 0 THEN 1 ELSE 0 END) AS human_injury_forms,
                SUM(CASE WHEN humanDeathAmount > 0 THEN 1 ELSE 0 END) AS human_death_forms,
                SUM(CASE WHEN Status IN ('1','2','3','4','5') THEN 1 ELSE 0 END) AS pending_forms,
                SUM(CASE WHEN Status = '6' THEN 1 ELSE 0 END) AS accepted_forms,
                SUM(CASE WHEN Status = '-1' THEN 1 ELSE 0 END) AS rejected_forms,
                SUM(CASE WHEN AnimalName = 'Elephant (हाथी)' THEN 1 ELSE 0 END) AS elephant_count,
                SUM(CASE WHEN AnimalName = 'Leopard (तेंदुआ)' THEN 1 ELSE 0 END) AS leopard_count,
                SUM(CASE WHEN AnimalName = 'Tiger (बाघ)' THEN 1 ELSE 0 END) AS tiger_count,
                SUM(CASE WHEN AnimalName = 'Sloth Bear (कंबल भालू)' THEN 1 ELSE 0 END) AS sloth_bear_count,
                SUM(CASE WHEN AnimalName = 'Hyena (हाइना)' THEN 1 ELSE 0 END) AS hyena_count,
                SUM(CASE WHEN AnimalName = 'Wild Boar (जंगली सूअर)' THEN 1 ELSE 0 END) AS wild_boar_count,
                SUM(CASE WHEN AnimalName = 'Jungle Cat (जंगल बिल्ली)' THEN 1 ELSE 0 END) AS jungle_cat_count
            FROM compensationform
            WHERE Circle_CG = %s AND Division = %s
        """
        cursor.execute(stats_query, (circle, division))
        stats = cursor.fetchone()

        if not stats or stats["total_forms"] == 0:
            return jsonify({"message": "No data found for this division"}), 404

        # 2. Fetch all forms
        forms_query = """
            SELECT FormID, SubmissionDateTime,ForestGuardID, complaint_id, ApplicantName, Mobile, IncidentDate,Circle_CG, Circle1,division,subdivision,range_,beat,statusHistory, AnimalName,totalCompensationAmount,lat,longitude
            FROM compensationform
            WHERE Circle_CG = %s AND division = %s
        """
        cursor.execute(forms_query, (circle, division))
        forms_records = cursor.fetchall()

        forms_list = []
        animal_names = []
        for form in forms_records:
            try:
                status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
            except json.JSONDecodeError:
                status_history = []
            forms_list.append({
                "formID": form["FormID"],
                "forestGuardID": form["ForestGuardID"],
                "submissionDateTime":form["SubmissionDateTime"],
                "totalCompensationAmount": form["totalCompensationAmount"],
                "complaint_id": form["complaint_id"],
                "applicantName": form["ApplicantName"],
                "mobile": form["Mobile"],
                "incidentDate": form["IncidentDate"],
                "circle_CG": form["Circle_CG"],
                "circle1": form["Circle1"],
                "division": form["division"],
                "subdivision": form["subdivision"],
                "range_": form["range_"],
                "beat": form["beat"],
                "statusHistory": status_history,
                "AnimalName":form["AnimalName"],
                "lat":form["lat"],
                "long":form["longitude"]
            })

            if form.get("AnimalName"):
                animal_names.append(form["AnimalName"])

        # Most frequent animal
        most_common_animal = Counter(animal_names).most_common(1)
        top_animal = most_common_animal[0][0] if most_common_animal else None

        return jsonify({
            "totalCompensationAmount": round(stats['total_compensation'] or 0, 2),
            "averageCompensationAmount": round(stats['avg_compensation'] or 0, 2),
            "totalForms": stats['total_forms'] or 0,

            "mostFrequentAnimal": top_animal,

            "statusWiseCounts":{
                "totalPendingForms": int(stats['pending_forms'] or 0),
                "totalAcceptedForms": int(stats['accepted_forms'] or 0),
                "totalRejectedForms": int(stats['rejected_forms'] or 0),

            },
            "damageWiseCounts":{
                "cattleInjuryForms": int(stats['cattle_injury_forms'] or 0),
                "cropDamageForms": int(stats['crop_damage_forms'] or 0),
                "houseDamageForms": int(stats['house_damage_forms'] or 0),
                "humanDeathForms": int(stats['human_death_forms'] or 0),
                "humanInjuryForms": int(stats['human_injury_forms'] or 0),

            },
            "damageWiseAmounts":{
                "totalCropDamageAmount": round(stats['total_crop_damage'] or 0, 2),
                "totalHouseDamageAmount": round(stats['total_house_damage'] or 0, 2),
                "totalCattleInjuryAmount": round(stats['total_cattle_injury'] or 0, 2),
                "totalHumanInjuryAmount": round(stats['total_human_injury'] or 0, 2),
                "totalHumanDeathAmount": round(stats['total_human_death'] or 0, 2),
                
            },
            "animalWiseCounts": {
                "Elephant (हाथी)": stats['elephant_count'],
                "Leopard (तेंदुआ)": stats['leopard_count'],
                "Tiger (बाघ)": stats['tiger_count'],
                "Sloth Bear (कंबल भालू)": stats['sloth_bear_count'],
                "Hyena (हाइना)": stats['hyena_count'],
                "Wild Boar (जंगली सूअर)": stats['wild_boar_count'],
                "Jungle Cat (जंगल बिल्ली)": stats['jungle_cat_count'],
            },
            "forms": forms_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    # data = request.json
    # emp_id = data.get('emp_id')
    # circle = data.get('circle')
    # division = data.get('division')  


    # if not circle or not division or not emp_id:
    #     return jsonify({"error": "Missing required field: circle or division or empId"}), 400

    # # Compare JWT emp_id with forestGuardID from request
    # if str(decoded_data.get("emp_id")) != str(emp_id):
    #     return jsonify({"error": "Unauthorized access"}), 403



    # connection = create_connection()
    # if not connection:
    #     return jsonify({"error": "Database connection failed"}), 500

    # try:
    #     cursor = connection.cursor(dictionary=True)

    #     base_query = "SELECT * FROM compensationform WHERE Circle_CG = %s"
    #     values = [circle]

    #     if division:
    #         base_query += " AND division = %s"
    #         values.append(division)

    #     cursor.execute(base_query, tuple(values))
    #     records = cursor.fetchall()

    #     if not records:
    #         return jsonify({"message": "No data found"}), 404

    #     total_sum = sum([float(r['totalCompensationAmount'] or 0) for r in records])
    #     avg_amount = total_sum / len(records) if records else 0
    #     count_forms = len(records)

    #     animals = [r['AnimalName'] for r in records if r['AnimalName']]
    #     most_common_animal = Counter(animals).most_common(1)
    #     top_animal = most_common_animal[0][0] if most_common_animal else None

    #     # Formatting form data
    #     result = []
    #     for form in records:
    #         try:
    #             status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
    #         except json.JSONDecodeError:
    #             status_history = []

    #         form_data = {
    #             "formID": form["FormID"],
    #             "forestGuardID": form["ForestGuardID"],
    #             "complaint_id": form["complaint_id"],
    #             "applicantName": form["ApplicantName"],
    #             "mobile": form["Mobile"],
    #             "incidentDate": form["IncidentDate"],
    #             "statusHistory": status_history,
    #         }
    #         result.append(form_data)

    #     return jsonify({
    #         "totalCompensationAmount": round(total_sum, 2),
    #         "averageCompensationAmount": round(avg_amount, 2),
    #         "totalForms": count_forms,
    #         "mostFrequentAnimal": top_animal,
    #         "forms": result
    #     }),200

    # except Error as e:
    #     return jsonify({"error": str(e)}), 500
    # finally:
    #     if connection.is_connected():
    #         cursor.close()
    #         connection.close()