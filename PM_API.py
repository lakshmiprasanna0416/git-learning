import math, bcrypt, random, os, secrets, time, logging, json, jwt, requests
from flask import Flask, request, jsonify, session
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from threading import Thread
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from threading import Thread
from flask_socketio import SocketIO

import MySQLdb
import hashlib
import random
import string

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)

app.secret_key = 'e486f9a541b4cf6b8a88d7ee9cfb49a5'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'new_jiffy'

# File upload configurations
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx'}
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configure Flask-Mail for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'rajubhaaik@gmail.com'
app.config['MAIL_PASSWORD'] = 'xmxb xwzg jvzn yyxk'
app.config['MAIL_DEFAULT_SENDER'] = ('JIFFY Team', 'rajubhaaik@gmail.com')

mysql = MySQL(app)
mail = Mail(app)


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_meeting_email(to_email, subject, body):
    msg = Message(subject, sender='rajubhaaik@gmail.com', recipients=[to_email])
    msg.body = body
    # logging.debug(f'Sending email to {to_email} with subject "{subject}"')
    Thread(target=send_async_email, args=(app, msg)).start()

def send_admin_notification_email(admin_email, firstname, lastname):
    subject = "New User Registration"
    body = f"Hello Admin,\n\nA new user {firstname} {lastname} has registered on your website."
    send_meeting_email(admin_email, subject, body)
    

# POST API to create a new team
@app.route('/api/create_team/<string:company_id>/<string:creator_id>', methods=['POST'])
def create_team(company_id, creator_id):
    data = request.json

    team_name = data.get('team_name')
    employee_ids = data.get('employee_ids') 
    team_lead_id = data.get('team_lead_id')
    team_description = data.get('team_description')

    if not all([team_name, employee_ids, team_lead_id]):
        return jsonify({"error": "Please provide all necessary fields."}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT role FROM employees WHERE employee_id = %s", (creator_id,))
        role = cur.fetchone()

        if not role or role[0] != 'Project Manager':
            return jsonify({"error": "Only users with the Project Manager role can create a team."}), 403

        employee_ids_str = ','.join(map(str, employee_ids))

        query = """
        INSERT INTO create_team (team_name, employee_ids, team_lead_id, team_description, company_id, creator_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (team_name, employee_ids_str, team_lead_id, team_description, company_id, creator_id))
        
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Team created successfully"}), 201
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500

# PUT API  to update the team details
@app.route('/api/update_team/<string:company_id>/<int:team_id>/<string:creator_id>', methods=['PUT'])
def update_team(team_id, company_id, creator_id):
    data = request.json

    team_name = data.get('team_name')
    employee_ids = data.get('employee_ids')  
    team_lead_id = data.get('team_lead_id')
    team_description = data.get('team_description')

    if not any([team_name, employee_ids, team_lead_id, team_description]):
        return jsonify({"error": "Please provide at least one field to update."}), 400

    try:
        # Check if the creator has the role of Project Manager
        cur = mysql.connection.cursor()
        cur.execute("SELECT role FROM employees WHERE employee_id = %s", (creator_id,))
        role = cur.fetchone()

        if not role or role[0] != 'Project Manager':
            return jsonify({"error": "Only users with the Project Manager role can update a team."}), 403

        update_fields = []
        update_values = []

        if team_name:
            update_fields.append("team_name = %s")
            update_values.append(team_name)

        if employee_ids:
            employee_ids_str = ','.join(map(str, employee_ids))
            update_fields.append("employee_ids = %s")
            update_values.append(employee_ids_str)

        if team_lead_id:
            update_fields.append("team_lead_id = %s")
            update_values.append(team_lead_id)

        if team_description:
            update_fields.append("team_description = %s")
            update_values.append(team_description)

        update_values.extend([team_id, company_id])

        update_query = f"""
        UPDATE create_team
        SET {', '.join(update_fields)}
        WHERE team_id = %s AND company_id = %s
        """
        
        cur.execute(update_query, update_values)
        
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Team updated successfully"}), 200
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500


# Retrieve all the teams by specific company ID
@app.route('/getTeams/<string:company_id>', methods=['GET'])
def get_teams_by_company_id(company_id):
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT * FROM create_team WHERE company_id = %s", (company_id,))
        teams = cur.fetchall()
        cur.close()

        if not teams:
            return jsonify({"message": "No teams found for the provided company_id"}), 404

        teams_list = []
        for team in teams:
            team_dict = {
                "team_id": team[0],         
                "team_name": team[1],
                "team_description": team[2],        
                "employee_ids": team[3],   
                "team_lead_id": team[4],    
                "company_id": team[6],
                "creator_id": team[7]    
            }
            teams_list.append(team_dict)

        return jsonify(teams_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Retrieve the specific team by GET by team_id method
@app.route('/getTeam/<string:company_id>/<int:team_id>', methods=['GET'])
def get_team_by_id(team_id, company_id):
    try:
        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM create_team WHERE team_id = %s AND company_id = %s", (team_id, company_id))

        team = cur.fetchone()
        cur.close()
        if not team:
            return jsonify({"message": "No team found for the provided team_id and company_id"}), 404

        team_dict = {
            "team_id": team[0],         
                "team_name": team[1],
                "team_description": team[2],        
                "employee_ids": team[3],   
                "team_lead_id": team[4],    
                "company_id": team[6],
                "creator_id": team[7]   
        }
        return jsonify(team_dict), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete the team by creator_id and team_lead
@app.route('/deleteTeam/<string:company_id>/<int:team_id>/<string:creator_id>', methods=['DELETE'])
def delete_team(company_id, team_id, creator_id):
    try:
        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT * FROM create_team 
            WHERE team_id = %s AND company_id = %s AND creator_id = %s
            """, (team_id, company_id, creator_id))
        team = cur.fetchone()

        if not team:
            return jsonify({"error": "No matching team found for the provided IDs."}), 404

        cur.execute("DELETE FROM create_team WHERE team_id = %s AND company_id = %s", 
                    (team_id, company_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Team deleted successfully."}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500

# --------------------------------------meeting schedule module-------------------------------------------------------------

#to save the file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    filename = secure_filename(file.filename)
    file.save(f"./uploads/{filename}")  
    return filename



# POST API for schedule meeting by project manager or team leader

@app.route('/api/schedule_meeting/<string:company_id>/<string:scheduler_id>', methods=['POST'])
def schedule_meeting(company_id, scheduler_id):
   
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT role FROM employees WHERE employee_id = %s AND company_id = %s", (scheduler_id, company_id))
        result = cur.fetchone()

        if not result or result[0] not in ['Project Manager', 'Team Leader']:
            return jsonify({"error": "Only project managers or team leaders can schedule meetings."}), 403

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    project_id = request.form.get('project_id')
    meeting_type = request.form.get('meeting_type')
    meeting_link = request.form.get('meeting_link')
    meeting_location = request.form.get('meeting_location')
    subject = request.form.get('subject')
    participants_id = request.form.get('participants_id', '')
    participants_id_list = participants_id.split(',') if participants_id else []
    meeting_date = request.form.get('meeting_date')
    status = 'Not Started'

    if not all([start_time, end_time, project_id, meeting_type, subject, participants_id_list, meeting_date, company_id]):
        return jsonify({"error": "All fields are required"}), 400

    if meeting_type.strip().lower() not in ['online', 'offline']:
        return jsonify({"error": "Invalid meeting type. Must be either 'online' or 'offline'"}), 400

    # Conditional validation for meeting type
    if meeting_type == 'offline' and not meeting_location:
        return jsonify({"error": "Meeting location is required for offline meetings"}), 400
    if meeting_type == 'online' and not meeting_link:
        return jsonify({"error": "Meeting link is required for online meetings"}), 400

    try:
        cur = mysql.connection.cursor()

        # Fetch the project name based on project_id
        cur.execute("SELECT project_name FROM projects WHERE id = %s AND company_id = %s", (project_id, company_id))
        project_name = cur.fetchone()
        if project_name:
            project_name = project_name[0]
        else:
            return jsonify({"error": "Invalid project ID"}), 400

        # Insert meeting details
        insert_query = """
            INSERT INTO meeting_schedule (company_id, project_id, meeting_date, start_time, end_time, 
                                          meeting_type, meeting_location, meeting_link, participants_id, subject, 
                                          scheduler_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (
            company_id, project_id, meeting_date, start_time, end_time,
            meeting_type, meeting_location, meeting_link, ",".join(participants_id_list), subject,
            scheduler_id, status
        ))

        mysql.connection.commit()

        # Fetch emails and names of participants and scheduler
        participant_emails = []
        participants_names = []
        if participants_id_list:
            placeholders = ','.join(['%s'] * len(participants_id_list))
            cur.execute(f"SELECT email, full_name FROM employees WHERE employee_id IN ({placeholders}) AND company_id = %s", (*participants_id_list, company_id))
            participants_data = cur.fetchall()
            participant_emails = [row[0] for row in participants_data]
            participants_names = [row[1] for row in participants_data]

        # Get scheduler email
        cur.execute("SELECT email FROM employees WHERE employee_id = %s AND company_id = %s", (scheduler_id, company_id))
        scheduler_email = cur.fetchone()[0]

        # Send meeting notifications
        send_meeting_notifications(scheduler_email, participant_emails, project_name, subject, meeting_date, start_time, end_time, meeting_type, meeting_location, meeting_link, participants_names, status)

        # Emit a Socket.IO notification to participants
        socketio.emit('meeting_scheduled', {
            'company_id': company_id,
            'project_id': project_id,
            'meeting_date': meeting_date,
            'start_time': start_time,
            'end_time': end_time,
            'meeting_type': meeting_type,
            'meeting_location': meeting_location,
            'meeting_link': meeting_link,
            'subject': subject,
            'scheduler_id': scheduler_id,
            'participants_id': participants_id_list,
            'status': status
        }, room=scheduler_id)

        # Notify each participant individually if they are online
        for participant_id in participants_id_list:
            socketio.emit('meeting_invitation', {
                'company_id': company_id,
                'project_id': project_id,
                'meeting_date': meeting_date,
                'start_time': start_time,
                'end_time': end_time,
                'meeting_type': meeting_type,
                'meeting_location': meeting_location,
                'meeting_link': meeting_link,
                'subject': subject,
                'scheduler_id': scheduler_id,
                'status': status
            }, room=participant_id)

        cur.close()

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500

    meeting_data = {
        "company_id": company_id,
        "project_id": project_id,
        "meeting_date": meeting_date,
        "start_time": start_time,
        "end_time": end_time,
        "meeting_type": meeting_type,
        "meeting_location": meeting_location,
        "meeting_link": meeting_link,
        "participants_id": ",".join(participants_id_list),
        "subject": subject,
        "scheduler_id": scheduler_id,
        "status": status,
    }

    return jsonify({"message": "Meeting scheduled successfully", "data": meeting_data}), 201

def send_meeting_notifications(scheduler_email, participant_emails, project_name, subject, meeting_date, start_time, end_time, meeting_type, meeting_location, meeting_link, participants_names, status):
    # Meeting information template
    meeting_info = f"""
        <p><strong>Project Name:</strong> {project_name}</p>
        <p><strong>Subject:</strong> {subject}</p>
        <p><strong>Meeting Date:</strong> {meeting_date}</p>
        <p><strong>Start Time:</strong> {start_time}</p>
        <p><strong>End Time:</strong> {end_time}</p>
        <p><strong>Meeting Type:</strong> {meeting_type}</p>
        <p><strong>Location:</strong> {meeting_location if meeting_type == 'offline' else 'N/A'}</p>
        <p><strong>Link:</strong> {meeting_link if meeting_type == 'online' else 'N/A'}</p>
        <p><strong>Status:</strong> {status}</p>
    """

    # Email for scheduler
    scheduler_body = f"""
    <html>
        <body>
            <p><strong>You have scheduled the following meeting:</strong></p>
            {meeting_info}
        </body>
    </html>
    """
    send_scheduler_email(scheduler_email, "Meeting Scheduled Confirmation", scheduler_body)

    # Email for participants
    participant_body = f"""
    <html>
        <body>
            <p><strong>You have been invited to the following meeting:</strong></p>
            {meeting_info}
        </body>
    </html>
    """
    for email in participant_emails:
        send_email(email, "Meeting Invitation", participant_body)

def send_scheduler_email(to_email, subject, body):
    msg = Message(subject, sender='rajubhaaik@gmail.com', recipients=[to_email])
    msg.body = body
    Thread(target=send_async_email, args=(app, msg)).start()

def send_email(recipient, subject, body):
    msg = Message(subject, recipients=[recipient])
    msg.html = body
    Thread(target=send_async_email, args=(app, msg)).start()

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)



# Combined API to update both meeting status and MOM attachments
@app.route('/api/update_meeting/<string:meeting_id>/<string:company_id>/<string:scheduler_id>', methods=['PUT'])
def update_meeting(meeting_id, company_id, scheduler_id):
    mom_attachments_paths = []

    try:
        # Check if the user is a Project Manager or Team Leader
        cur = mysql.connection.cursor()
        cur.execute("SELECT role FROM employees WHERE employee_id = %s AND company_id = %s", (scheduler_id, company_id))
        result = cur.fetchone()
        
        if not result or result[0] not in ['Project Manager', 'Team Leader']:
            return jsonify({"error": "Only project managers or team leaders can update meetings."}), 403

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

    # Handle file uploads for MOM attachments
    if 'mom_attachments' in request.files:
        for mom_attachment in request.files.getlist('mom_attachments'):
            if mom_attachment.filename == '':
                return jsonify({"error": "No selected file"}), 400
            path = save_file(mom_attachment)
            if not path:
                return jsonify({"error": "File type not allowed"}), 400
            mom_attachments_paths.append(path)

    # Get optional fields from form
    fields = {
        "project_id": request.form.get('project_id'),
        "meeting_date": request.form.get('meeting_date'),
        "start_time": request.form.get('start_time'),
        "end_time": request.form.get('end_time'),
        "meeting_type": request.form.get('meeting_type'),
        "meeting_location": request.form.get('meeting_location'),
        "meeting_link": request.form.get('meeting_link'),
        "participants_id": ",".join(request.form.getlist('participants_id')),
        "subject": request.form.get('subject'),
        "status": request.form.get('status'),  # New field for status
        "mom_attachments": ",".join(mom_attachments_paths) if mom_attachments_paths else None,
    }

    # Update status based on action
    if fields['status'] == 'start':
        fields['status'] = 'In Progress'
    elif fields['status'] == 'stop':
        fields['status'] = 'Ended'
    elif fields['status'] and fields['status'] not in ['Not Started', 'In Progress', 'Ended']:
        return jsonify({"error": "Invalid status value. Use 'Not Started', 'In Progress', or 'Ended'."}), 400

    # Prepare the update query with conditional updates
    update_query = """
        UPDATE meeting_schedule
        SET 
            project_id = COALESCE(NULLIF(%s, ''), project_id),
            meeting_date = COALESCE(NULLIF(%s, ''), meeting_date),
            start_time = COALESCE(NULLIF(%s, ''), start_time),
            end_time = COALESCE(NULLIF(%s, ''), end_time),
            meeting_type = COALESCE(NULLIF(%s, ''), meeting_type),
            meeting_location = COALESCE(NULLIF(%s, ''), meeting_location),
            meeting_link = COALESCE(NULLIF(%s, ''), meeting_link),
            participants_id = COALESCE(NULLIF(%s, ''), participants_id),
            subject = COALESCE(NULLIF(%s, ''), subject),
            status = COALESCE(NULLIF(%s, ''), status),
            mom_attachments = COALESCE(NULLIF(%s, ''), mom_attachments)
        WHERE meeting_id = %s AND company_id = %s AND scheduler_id = %s
    """

    try:
        cur = mysql.connection.cursor()
        cur.execute(update_query, (
            fields['project_id'], fields['meeting_date'], fields['start_time'],
            fields['end_time'], fields['meeting_type'], fields['meeting_location'],
            fields['meeting_link'], fields['participants_id'], fields['subject'],
            fields['status'], fields['mom_attachments'], meeting_id, company_id, scheduler_id
        ))

        mysql.connection.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "No meeting found with the provided identifiers"}), 404

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

    return jsonify({"message": "Meeting updated successfully"}), 200


# Retrieve all the meeting schedules from database by GET by scheduler_id method
@app.route('/api/meetings/<string:company_id>', methods=['GET'])
@app.route('/api/meetings/<string:company_id>/<int:meeting_id>', methods=['GET'])
def get_meetings(company_id, meeting_id=None):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor for key-value pairs
    
    if meeting_id:
        # Fetch a specific meeting by ID and company_id
        cursor.execute("SELECT * FROM meeting_schedule WHERE meeting_id = %s AND company_id = %s", (meeting_id, company_id))
        meeting = cursor.fetchone()
        cursor.close()
        
        if not meeting:
            return jsonify({"error": "Meeting not found"}), 404
        return jsonify(meeting), 200  
    else:
        # Fetch all meetings for the given company_id if no meeting_id is provided
        cursor.execute("SELECT * FROM meeting_schedule WHERE company_id = %s", (company_id,))
        meetings = cursor.fetchall()
        cursor.close()
        
        if not meetings:
            return jsonify({"message": "No meetings found for the provided company ID."}), 404
            
        return jsonify(meetings), 200 

#-----------------------------employee details---------------------------------------------#

# Retrive all the employees based on company Id
@app.route('/api/employees/<string:company_id>', methods=['GET'])
def get_employees(company_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
    
    try:
        cursor.execute("SELECT * FROM employees WHERE company_id = %s", (company_id,))
        employees = cursor.fetchall()
        cursor.close()
        
        if not employees:
            return jsonify({"message": "No employees found for the provided company ID."}), 404
        
        return jsonify(employees), 200  

    except Exception as e:
        cursor.close()
        return jsonify({"error": str(e)}), 500


#----------------------------------------------- Profile -----------------------------------------------

# Route to retrieve employee details based on company_id and employee_id
@app.route('/api/employees/<string:company_id>/<string:employee_id>', methods=['GET'])
def get_employee_by_id(company_id, employee_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute("SELECT * FROM employees WHERE company_id = %s AND employee_id = %s", (company_id, employee_id))
        employee = cursor.fetchone()
        cursor.close()

        if not employee:
            return jsonify({"message": "No employee found for the provided company ID and employee ID."}), 404

        return jsonify(employee), 200  

    except Exception as e:
        cursor.close()
        return jsonify({"error": str(e)}), 500


# Route to update employee details based on company_id and employee_id using form data
@app.route('/api/update_employee/<string:company_id>/<string:employee_id>', methods=['PUT'])
def update_employee(company_id, employee_id):
    cursor = mysql.connection.cursor()

    try:
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        contact_number = request.form.get('contact_number')
        date_of_birth = request.form.get('date_of_birth')
        salary = request.form.get('salary')
        department = request.form.get('department')
        role = request.form.get('role')
        bank_account = request.form.get('bank_account')
        address = request.form.get('address')

        query = "UPDATE employees SET "
        updates = []
        params = []

        if full_name:
            updates.append("full_name = %s")
            params.append(full_name)
        if email:
            updates.append("email = %s")
            params.append(email)
        if contact_number:
            updates.append("contact_number = %s")
            params.append(contact_number)
        if date_of_birth:
            updates.append("date_of_birth = %s")
            params.append(date_of_birth)
        if salary:
            updates.append("salary = %s")
            params.append(salary)
        if department:
            updates.append("department = %s")
            params.append(department)
        if role:
            updates.append("role = %s")
            params.append(role)
        if bank_account:
            updates.append("bank_account = %s")
            params.append(bank_account)
        if address:
            updates.append("address = %s")
            params.append(address)

        if updates:
            query += ", ".join(updates) + " WHERE company_id = %s AND employee_id = %s"
            params.append(company_id)
            params.append(employee_id)

            cursor.execute(query, tuple(params))
            mysql.connection.commit()
            cursor.close()

            if cursor.rowcount == 0:
                return jsonify({"message": "No employee found to update with the provided company ID and employee ID."}), 404

            return jsonify({"message": "Employee details updated successfully."}), 200

        else:
            cursor.close()
            return jsonify({"message": "No fields provided for update."}), 400

    except Exception as e:
        cursor.close()
        return jsonify({"error": str(e)}), 500

#------------------------------------------- Employee Tracking --------------------------------------------------#

# Retrieve all the employee details based on current date to track the login and available details
@app.route('/api/employee_tracking/<string:company_id>', methods=['GET'])
def get_employee_tracking(company_id):
    try:
        cur = mysql.connection.cursor()

        # Query to retrieve attendance data with task details for current date
        query = """
            SELECT 
                a.date AS Date, 
                e.employee_id AS Employee_Name, 
                a.time_in AS Time_In, 
                a.time_out AS Time_Out, 
                CASE 
                    WHEN MAX(t.task_progress) = 'inprogress' THEN 'Busy' 
                    ELSE 'Available' 
                END AS Status, 
                TIMEDIFF(a.time_out, a.time_in) AS Total_Hours 
            FROM 
                attendance AS a 
            LEFT JOIN 
                employees AS e ON a.employee_id = e.employee_id 
            LEFT JOIN 
                tasks AS t ON e.employee_id = t.assign_to AND t.company_id = a.company_id 
            WHERE 
                a.company_id = %s AND 
                a.date = CURDATE() 
            GROUP BY 
                a.employee_id;
        """
        
        # Execute the query
        cur.execute(query, (company_id,))
        results = cur.fetchall()

        # Check if data was returned
        if not results:
            return jsonify({"message": "No attendance or task data found for the current date."}), 404
        
        # Format the results for response
        response_data = []
        for row in results:
            total_hours = row[5]  # `Total_Hours` is the result of TIMEDIFF
            if total_hours:
                total_seconds = int(total_hours.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                total_hours_str = f"{hours}:{minutes:02}" 
            else:
                total_hours_str = "0:00"  

            response_data.append({
                "Date": row[0],
                "Employee_Name": row[1],
                "Time_In": row[2],
                "Time_Out": row[3],
                "Status": row[4],
                "Total_Hours": total_hours_str 
            })

        # Return the formatted response
        return jsonify({"data": response_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()


#------------------------------------------- Employee Report --------------------------------------------------#

# API to fetch Employee Report based on company_id
@app.route('/api/employee_report/<string:company_id>/<string:employee_id>', methods=['GET'])
def get_employee_report(company_id, employee_id):
    cursor = mysql.connection.cursor()
    
    query = """
        SELECT 
            p.project_name, 
            t.task_name AS task, 
            t.actual_start_date AS start_date, 
            t.actual_end_date AS end_date,
            TIMESTAMPDIFF(HOUR, t.actual_start_date, t.actual_end_date) AS task_duration
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        LEFT JOIN employees e ON t.assign_to = e.employee_id  -- Assuming there's an employee table
        WHERE p.company_id = %s AND t.assign_to = %s
    """
    
    cursor.execute(query, (company_id, employee_id))
    result = cursor.fetchall()
    
    response_data = []
    for row in result:
        response_data.append({
            "Project_Name": row[0],
            "Task": row[1],
            "Start_Date": row[2],
            "End_Date": row[3],
            "Task_Duration": f"{row[4]} hours"
        })
    
    if not response_data:
        return jsonify({"message": "No data found for the given company_id and employee_id"}), 404
    
    return jsonify({"data": response_data}), 200


#------------------------------------------- Task Module percentage --------------------------------------------------#
#SELECT module_name, COUNT(task_id) AS total_tasks, SUM(CASE WHEN task_progress = 'completed' THEN 1 ELSE 0 END) AS completed_tasks, (SUM(CASE WHEN task_progress = 'completed' THEN 1 ELSE 0 END) / COUNT(task_id)) * 100 AS module_completion_percentage FROM tasks WHERE project_id = '4' -- Replace with your actual project_id GROUP BY module_name;
# -- Get total modules and their completion percentages
# WITH ModuleCompletion AS (
#     SELECT
#         TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(p.module_name, ',', numbers.n), ',', -1)) AS module_name,
#         IFNULL(t.total_tasks, 0) AS total_tasks,
#         IFNULL(t.completed_tasks, 0) AS completed_tasks,
#         IFNULL(t.module_completion_percentage, 0) AS module_completion_percentage
#     FROM
#         projects p
#     INNER JOIN (
#         SELECT 1 n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
#         UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
#         UNION ALL SELECT 9 UNION ALL SELECT 10
#     ) numbers ON CHAR_LENGTH(p.module_name) - CHAR_LENGTH(REPLACE(p.module_name, ',', '')) >= numbers.n - 1
#     LEFT JOIN (
#         SELECT
#             module_name,
#             COUNT(task_id) AS total_tasks,
#             SUM(CASE WHEN task_progress = 'completed' THEN 1 ELSE 0 END) AS completed_tasks,
#             (SUM(CASE WHEN task_progress = 'completed' THEN 1 ELSE 0 END) / COUNT(task_id)) * 100 AS module_completion_percentage
#         FROM
#             tasks
#         WHERE
#             project_id = '4' -- Replace with your actual project_id
#         GROUP BY
#             module_name
#     ) t ON TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(p.module_name, ',', numbers.n), ',', -1)) = t.module_name
#     WHERE
#         p.id = '4' -- Replace with your actual project_id
# ),

# -- Calculate total project percentage
# TotalProjectPercentage AS (
#     SELECT
#         SUM(module_completion_percentage) AS total_completion_percentage,
#         COUNT(module_name) AS total_modules
#     FROM
#         ModuleCompletion
# )

# SELECT
#     mc.module_name,
#     mc.total_tasks,
#     mc.completed_tasks,
#     mc.module_completion_percentage,
#     ((SELECT total_completion_percentage FROM TotalProjectPercentage) / 
#     (SELECT total_modules FROM TotalProjectPercentage)) AS total_project_percentage
# FROM
#     ModuleCompletion mc
# ORDER BY
#     mc.module_name;


# GET API to fetch project modules
@app.route('/api/get_all_project_modules/<string:company_id>/<string:project_id>', methods=['GET'])
def get_all_project_modules(company_id, project_id):
    query = """
        WITH ModuleCompletion AS (
            SELECT
                TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(p.module_names, ',', numbers.n), ',', -1)) AS module_name,
                IFNULL(t.total_tasks, 0) AS total_tasks,
                IFNULL(t.completed_tasks, 0) AS completed_tasks,
                IFNULL(t.module_completion_percentage, 0) AS module_completion_percentage
            FROM
                projects p
            INNER JOIN (
                SELECT 1 n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
                UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
                UNION ALL SELECT 9 UNION ALL SELECT 10
            ) numbers ON CHAR_LENGTH(p.module_names) - CHAR_LENGTH(REPLACE(p.module_names, ',', '')) >= numbers.n - 1
            LEFT JOIN (
                SELECT
                    module_name,
                    COUNT(task_id) AS total_tasks,
                    SUM(CASE WHEN task_progress = 'completed' THEN 1 ELSE 0 END) AS completed_tasks,
                    (SUM(CASE WHEN task_progress = 'completed' THEN 1 ELSE 0 END) / COUNT(task_id)) * 100 AS module_completion_percentage
                FROM
                    tasks
                WHERE
                    project_id = %s
                GROUP BY
                    module_name
            ) t ON TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(p.module_names, ',', numbers.n), ',', -1)) = t.module_name
            WHERE
                p.company_id = %s AND p.id = %s
        ),
        TotalProjectPercentage AS (
            SELECT
                SUM(module_completion_percentage) / COUNT(module_name) AS total_project_percentage
            FROM
                ModuleCompletion
        )
        SELECT
            mc.module_name,
            mc.total_tasks,
            mc.completed_tasks,
            mc.module_completion_percentage,
            tp.total_project_percentage
        FROM
            ModuleCompletion mc,
            TotalProjectPercentage tp
    """
    
    cur = mysql.connection.cursor()
    cur.execute(query, (project_id, company_id, project_id))
    modules = cur.fetchall()
    cur.close()

    if not modules:
        return jsonify({"error": "Project or modules not found"}), 404

    project_modules = [
        {
            "module_name": module[0],
            "total_tasks": module[1],
            "completed_tasks": module[2],
            "module_completion_percentage": module[3]
        }
        for module in modules
    ]
    total_project_percentage = modules[0][4] if modules else 0  # Get total project percentage from first row

    return jsonify({
        "project_modules": project_modules,
        "total_project_percentage": total_project_percentage
    }), 200




#--------------------------------Landing Page -----------------------------------------#
import hashlib
import random
import string

def generate_token(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# POST Api for user Register 
@app.route('/register', methods=['POST'])
def register_user():
    # Get form data from the request
    companyName = request.form.get('companyName')
    country = request.form.get('country')
    city = request.form.get('city')
    address = request.form.get('address')
    contactPersonName = request.form.get('contactPersonName')
    contactEmail = request.form.get('contactEmail')
    phoneNumber = request.form.get('phoneNumber')
    jiffyPlan = request.form.get('jiffyPlan')
    businessType = request.form.get('businessType')
    numberOfEmployees = request.form.get('numberOfEmployees')
    websiteURL = request.form.get('websiteURL')
    
    # Validate required fields
    if not companyName or not contactEmail or not phoneNumber:
        return jsonify({"error": "Missing required fields"}), 400

    
    
    # Generate verification token and set expiration time
    token = generate_token()
    expiration_time = datetime.now() + timedelta(hours=24)  # Token expires in 24 hours

    # Insert data into UserRegistration table
    cur = mysql.connection.cursor()
    registration_query = """
    INSERT INTO UserRegistration 
    (companyName, country, city, address, contactPersonName, contactEmail, 
     phoneNumber, jiffyPlan, businessType, numberOfEmployees, websiteURL) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    registration_values = (companyName, country, city, address, contactPersonName, contactEmail, 
                           phoneNumber, jiffyPlan, businessType, numberOfEmployees, websiteURL)
    cur.execute(registration_query, registration_values)
    mysql.connection.commit()

    # Insert token data into user_verification table
    verification_query = """
    INSERT INTO user_verification 
    (user_email, verification_token, expiration_time, is_verified) 
    VALUES (%s, %s, %s, %s)
    """
    verification_values = (contactEmail, token, expiration_time, False)
    cur.execute(verification_query, verification_values)
    mysql.connection.commit()
    cur.close()

    # Send verification email with the token link
    verification_link = f"http://localhost:5000/verify/{token}"
    msg = Message("Welcome to Jiffy! Complete Your Account Setup",
                  recipients=[contactEmail])
    msg.body = f"""Hi {contactPersonName},
    
Thank you for selecting the {jiffyPlan} plan. To complete your account setup, please click the link below:
{verification_link}

If you have any issues, feel free to reach out to our support team.

Best Regards,
Jiffy Team
"""
    mail.send(msg)

    return jsonify({"message": "User registered successfully. Verification email sent."}), 201

# GET api for user register
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    try:
        # Connect to the database and create a cursor
        cur = mysql.connection.cursor()
        
        # Query to fetch user details by ID
        query = """
        SELECT companyName, country, city, address, contactPersonName, 
               contactEmail, phoneNumber, jiffyPlan, businessType, 
               numberOfEmployees, websiteURL
        FROM UserRegistration
        WHERE id = %s
        """
        cur.execute(query, (user_id,))
        user = cur.fetchone()
        
        # If no user is found, return a 404 error
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Construct a response object with the user details
        user_details = {
            "companyName": user[0],
            "country": user[1],
            "city": user[2],
            "address": user[3],
            "contactPersonName": user[4],
            "contactEmail": user[5],
            "phoneNumber": user[6],
            "jiffyPlan": user[7],
            "businessType": user[8],
            "numberOfEmployees": user[9],
            "websiteURL": user[10]
        }
        
        return jsonify({"user": user_details}), 200
    
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
    finally:
        cur.close()



# GET API for fetch the email and phone number after user registration
@app.route('/employee_contact/<int:employee_id>', methods=['GET'])
def get_employee_contact(employee_id):
    cur = mysql.connection.cursor()
    employee_contact_query = """
    SELECT contactEmail, phoneNumber FROM UserRegistration 
    WHERE id = %s
    """
    cur.execute(employee_contact_query, (employee_id,))
    result = cur.fetchone()
    cur.close()

    if not result:
        return jsonify({"error": "Employee not found"}), 404

    registered_email, registered_phone = result
    masked_email = mask_email(registered_email)
    masked_phone = mask_phone(registered_phone)

    return jsonify({
        "maskedEmail": masked_email,
        "maskedPhone": masked_phone
    }), 200


def mask_email(email):
    if "@" not in email:
        return email
    
    local_part, domain = email.split("@")
    if len(local_part) <= 4:
        masked_local = "*" * len(local_part)
    else:
        visible_part = local_part[-4:]
        masked_local = "*" * (len(local_part) - 4) + visible_part

    return f"{masked_local}@{domain}"


def mask_phone(phone):
    if len(phone) <= 4:
        return "*" * len(phone)
    else:
        visible_part = phone[-4:]
        masked_part = "*" * (len(phone) - 4)
        return f"{masked_part}{visible_part}"



def generate_verification_link(contact_email):
    # Generate a unique verification link using a hash and timestamp
    unique_token = hashlib.sha256(f'{contact_email}{time.time()}'.encode('utf-8')).hexdigest()
    verification_link = f"https://jiffy.mineit.tech/?token={unique_token}"
    return verification_link


def send_account_creation_email(contact_email, contact_person_name, jiffy_plan, verification_link):
    # Create the email message
    subject = "Welcome to Jiffy! Complete Your Account Setup"
    body = f"""
    Hi {contact_person_name},

    Thank you for selecting the {jiffy_plan} plan. To complete your account setup, please click the link below:

    {verification_link}

    This link will expire in 24 hours, so please complete the registration soon.

    If you have any issues, feel free to reach out to our support team at support@jiffy.com.

    Best Regards,
    Jiffy Team
    """

    msg = Message(subject, recipients=[contact_email])
    msg.body = body

    # Send the email
    mail.send(msg)


# GET Api for verify using token

@app.route('/verify/<token>', methods=['GET'])
def verify_account(token):
    # Step 1: Find the verification record based on the token
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user_verification WHERE verification_token = %s", (token,))
    verification_record = cur.fetchone()

    if not verification_record:
        return jsonify({"error": "Invalid or expired token."}), 400
    
    # Step 2: Check if the token is expired
    expiration_time = verification_record[3]
    if datetime.now() > expiration_time:
        return jsonify({"error": "Verification link has expired."}), 400
    
    # Step 3: Fetch the user details
    cur.execute("SELECT * FROM UserRegistration WHERE contactEmail = %s", (verification_record[1],))
    user_data = cur.fetchone()

    if not user_data:
        return jsonify({"error": "User not found."}), 404

    # Return the user data along with the taxID field to be added
    user_info = {
        "companyName": user_data[1],
        "country": user_data[2],
        "city": user_data[3],
        "address": user_data[4],
        "contactPersonName": user_data[5],
        "contactEmail": user_data[6],
        "phoneNumber": user_data[7],
        "jiffyPlan": user_data[8],
        "businessType": user_data[9],
        "numberOfEmployees": user_data[10],
        "websiteURL": user_data[11],
        "taxID": user_data[12] if user_data[14] else "",  
    }

    # Provide a form to update data
    return jsonify(user_info)    

# POST Api for conform user register
@app.route('/update_user/<string:company_id>', methods=['POST'])
def update_user_data(company_id):
    # Get data from the request (optional fields)
    taxID = request.form.get('taxID')  # Required field
    companyName = request.form.get('companyName')
    country = request.form.get('country')
    city = request.form.get('city')
    address = request.form.get('address')
    contactPersonName = request.form.get('contactPersonName')
    contactEmail = request.form.get('contactEmail')
    phoneNumber = request.form.get('phoneNumber')
    jiffyPlan = request.form.get('jiffyPlan')
    businessType = request.form.get('businessType')
    numberOfEmployees = request.form.get('numberOfEmployees')
    websiteURL = request.form.get('websiteURL')

    # Validate required field `taxID`
    if not taxID:
        return jsonify({"error": "taxID is a required field"}), 400

    # Build the dynamic SQL query based on provided fields
    update_fields = []
    values = []

    if companyName:
        update_fields.append("companyName = %s")
        values.append(companyName)
    if country:
        update_fields.append("country = %s")
        values.append(country)
    if city:
        update_fields.append("city = %s")
        values.append(city)
    if address:
        update_fields.append("address = %s")
        values.append(address)
    if contactPersonName:
        update_fields.append("contactPersonName = %s")
        values.append(contactPersonName)
    if contactEmail:
        update_fields.append("contactEmail = %s")
        values.append(contactEmail)
    if phoneNumber:
        update_fields.append("phoneNumber = %s")
        values.append(phoneNumber)
    if jiffyPlan:
        update_fields.append("jiffyPlan = %s")
        values.append(jiffyPlan)
    if businessType:
        update_fields.append("businessType = %s")
        values.append(businessType)
    if numberOfEmployees:
        update_fields.append("numberOfEmployees = %s")
        values.append(numberOfEmployees)
    if websiteURL:
        update_fields.append("websiteURL = %s")
        values.append(websiteURL)

    # Always update `taxID` as it is mandatory
    update_fields.append("taxID = %s")
    values.append(taxID)

    # Append the `id` for the WHERE clause
    values.append(company_id)

    # Construct the SQL query
    query = f"UPDATE UserRegistration SET {', '.join(update_fields)} WHERE company_id = %s"

    # Execute the query
    cur = mysql.connection.cursor()
    cur.execute(query, tuple(values))
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "User data updated successfully."}), 200


if __name__ == '__main__':
    app.run(debug=True)