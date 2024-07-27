import os
from flask import Blueprint, flash, jsonify, render_template, request, session, redirect, url_for
from flask_login import current_user, login_required
import pytz
import requests
import pyrebase
from app.config import Config
from app.routes.auth import firebase_db
from ..models_db import Patient, Doctor, Appointment, Message, Prescription, Settings, User, ClientAccounts
from .. import sqlalchemy_db as db



bp = Blueprint('amdin', __name__)