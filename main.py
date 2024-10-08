# Importar dependencias
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import HTMLResponse
from typing import Annotated
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from auth import router, SECRET_KEY, ALGORITHM
from jose import jwt
from enum import Enum
from dotenv import load_dotenv
import psycopg2
import os 

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
# Inicializar la aplicación FastAPI
app = FastAPI()
# Incluir el router de autenticación definido en auth.py
app.include_router(router)

# Permitir CORS para todas las orígenes (*)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Definir el modelo Pydantic para representar un ticket
class Ticket(BaseModel):
    user_id: int
    title: str
    description: str
    status: str
    category: str
    priority: str

# Enums para definir los valores permitidos en los campos de tickets
class Status(str, Enum):
    abierto = "abierto"
    cerrado = "cerrado"

class Category(str, Enum):
    network = "network"
    software = "software"
    hardware = "hardware"

class Priority(str, Enum):
    baja = "baja"
    media = "media"
    alta = "alta"

# Modelo de entrada para crear un ticket con validaciones en los campos
class Ticket_create(BaseModel):
    Ticket_id: int
    title: str = Field(min_length=5, max_length=25)
    description: str = Field(min_length=5, max_length=50)
    status: Status
    category: Category
    priority: Priority
    created_at: datetime = None
    updated_at: datetime = None    

"""
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    title VARCHAR(255),
    description TEXT,
    status CHAR(1),
    category VARCHAR(100),
    priority VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

DATABASE_URL = os.getenv('PG_APIKEY')
# Función para conectar a la base de datos PostgreSQL
def conectar_bd():
    conexion = psycopg2.connect(
        DATABASE_URL #"postgresql://user:password@localhost/mydatabase"
    )
    return conexion

# Función para cerrar la conexión a la base de datos
def cerrar_bd(conexion):
    conexion.close()

# ♣-♥-♦ CREATE - POST # Endpoint para crear un nuevo ticket
@app.post('/ticket/', response_model=Ticket, tags=["Ticket"], description="Create a new ticket")
def create_ticket(ticket: Ticket_create):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = """
    INSERT INTO tickets (user_id, title, description, status, category, priority, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW()) RETURNING *;
    """
    cursor.execute(query, (
        ticket.user_id, ticket.title, ticket.description, ticket.status, ticket.category, ticket.priority
    ))
    new_ticket = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()
    # Retornar todos los tickets como una lista de diccionarios
    return dict(zip([desc[0] for desc in cursor.description], new_ticket))

# doc, url, sql, front
# ♣-♥-♦ READ - GET # Endpoint para obtener todos los tickets (solo usuarios autorizados)
@app.get('/ticket/', tags=["Ticket"])
def get_tickets(token: Annotated[str | None, Header()] = None):
    
    if token is None:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usted no se encuentra autorizado",
            headers={"auth": "Bearer"}, # se contesta como consideres el error
        )
    # Decodificar el token JWT para obtener el rol del usuario
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    rol: str = payload.get("rol")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    sql = "SELECT * FROM tickets;"
    if rol == "user": 
        sql = "SELECT * FROM tickets WHERE user_id = 1"
    cursor.execute(sql)
    Ticket = cursor.fetchall() 
    cursor.close()
    conexion.close()
    return [dict(zip([desc[0] for desc in cursor.description], ticket)) for ticket in Ticket]
    
    raise HTTPException(status_code=401, detail="Do't have a permissions to request")  
    

# READ - GET by ID # Endpoint para obtener un ticket por su ID
@app.get('/ticket/{ticket_id}', response_model=Ticket, tags=["Ticket"])
def get_ticket(ticket_id: int):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Consulta para obtener un ticket específico por ID
    cursor.execute("SELECT * FROM tickets WHERE id = %s;", (ticket_id,))
    ticketfin = cursor.fetchone()
    cursor.close()
    conexion.close()

    if ticketfin is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    
    print(ticketfin)
    return dict(zip([desc[0] for desc in cursor.description], ticketfin))


# UPDATE - PUT # Endpoint para actualizar un ticket
@app.put('/ticket/{ticket_id}', response_model=Ticket, tags=["Ticket"])
def update_ticket(ticket_id: int, ticket: Ticket):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    query = """
    UPDATE ticket
    SET user_id = %s, title = %s, description = %s, status = %s, category = %s, priority = %s, updated_at = NOW()
    WHERE id = %s RETURNING *;
    """

    cursor.execute(query, (
        ticket.user_id, ticket.title, ticket.description, ticket.status, ticket.category, ticket.priority, ticket_id
    ))
    update_ticket = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()

    if update_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return dict(zip([desc[0] for desc in cursor.description], update_ticket))


# DELETE - DELETE # Endpoint para eliminar un ticket
@app.delete('/ticket/{ticket_id}', response_model=dict, tags=["Ticket"])
def deleted_ticket(ticket_id: int):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM tickets WHERE id = %s RETURNING id;", (ticket_id,))
    deleted_ticket = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()

    if deleted_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {"message": "Ticket deleted successfully", "id": deleted_ticket[0]}