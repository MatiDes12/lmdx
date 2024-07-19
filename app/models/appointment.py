class Appointment:
    def __init__(self, appointment_id, user_id, doctor_id, date, time, reason):
        self.appointment_id = appointment_id
        self.user_id = user_id
        self.doctor_id = doctor_id
        self.date = date
        self.time = time
        self.reason = reason