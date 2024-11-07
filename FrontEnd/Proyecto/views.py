import tempfile
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import FileForm
from django.views.decorators.csrf import csrf_exempt
import base64
import requests
import logging
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime
import json
import xml.dom.minidom

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

FLASK_API_URL = 'http://localhost:5000'

# Crear una sesión de requests que mantendrá las cookies entre solicitudes
flask_session = requests.Session()

@csrf_exempt
def store_chart_image(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_data = data['image']
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        if 'chart_images' not in request.session:
            request.session['chart_images'] = []
        request.session['chart_images'].append({
            'image': image_data,
            'timestamp': timestamp
        })
        request.session.modified = True
        return HttpResponse(status=200)
    return HttpResponse(status=400)

def index(request):
    context = {
        'xml_content': '',
        'processed_content': '',
        'error': ''
    }
    return render(request, 'index.html', context)

def cargar(request):
    return render(request, 'cargar.html')

def peticiones(request):
    context = {
        'processed_content': '',
        'error': ''
    }
    # Obtener el XML procesado desde la sesión
    processed_xml = request.session.get('processed_xml', '')
    if processed_xml:
        context['processed_content'] = processed_xml
    else:
        context['error'] = 'No hay datos procesados disponibles. Por favor, procesa un archivo primero.'
    return render(request, 'peticiones.html', context)

def consultar(request):
    context = {
        'processed_content': '',
        'error': ''
    }
    # Obtener el XML procesado desde la sesión
    processed_xml = request.session.get('processed_xml', '')
    if processed_xml:
        context['processed_content'] = processed_xml
    else:
        context['error'] = 'No hay datos procesados disponibles. Por favor, procesa un archivo primero.'
    return render(request, 'consultar.html', context)

def fecha(request):
    return render(request, 'fecha.html')

def rangoFecha(request):
    return render(request, 'rangoFecha.html')

def mensajes(request):
    return render(request, 'mensajes.html')

def ayuda(request):
    return render(request, 'ayuda.html')

def datos(request):
    return render(request, 'datos.html')

def format_xml(xml_string):
    """Formatea el XML con sangría adecuada y sin espacios adicionales"""
    try:
        # Si es un string válido de XML, formatearlo
        if isinstance(xml_string, str):
            # Remove literal '\n' strings and extra quotes
            xml_string = xml_string.replace('\\n', '\n').strip('"\'')
            
            if xml_string.strip().startswith('<?xml') or xml_string.strip().startswith('<'):
                dom = minidom.parseString(xml_string)
                formatted_xml = dom.toprettyxml(indent='  ')
                # Remove empty lines while preserving indentation
                lines = formatted_xml.split('\n')
                cleaned_lines = [line for line in lines if line.strip()]
                return '\n'.join(cleaned_lines)
        return xml_string
    except Exception as e:
        logger.error(f"Error formateando XML: {str(e)}")
        return xml_string

def remove_blank_lines(xml_string):
    """Elimina líneas en blanco manteniendo la indentación"""
    lines = xml_string.split('\n')
    return '\n'.join(line for line in lines if line.strip())


def procesar_datos(request):
    context = {
        'xml_content': '',
        'processed_content': '',
        'error': ''
    }
    
    if request.method == 'POST':
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            logger.debug(f"Archivo recibido: {archivo.name}")
            
            if not archivo.name.endswith('.xml'):
                context['error'] = 'El archivo debe ser XML'
                return render(request, 'cargar.html', context)
            
            try:
                # Read XML content
                xml_content = archivo.read()
                try:
                    xml_content = xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    xml_content = xml_content.decode('latin-1')
                
                # Store original content
                context['xml_content'] = xml_content
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as temp_file:
                    temp_file.write(xml_content.encode('utf-8'))
                    temp_filename = temp_file.name
                
                try:
                    # Send file to Flask backend
                    with open(temp_filename, 'rb') as f:
                        files = {
                            'archivo': ('archivo.xml', f, 'application/xml')
                        }
                        
                        # Make request to Flask backend
                        response = requests.post(
                            f'{FLASK_API_URL}/procesar_xml',
                            files=files,
                            timeout=30  # Add timeout
                        )
                        
                        logger.debug(f"Response status: {response.status_code}")
                        logger.debug(f"Response content: {response.content[:200]}...")  # Log first 200 chars
                        
                        if response.status_code == 200:
                            data = response.json()
                            processed_xml = data.get('xml_content', '')
                            
                            if processed_xml:
                                # Formatear el XML procesado
                                try:
                                    dom = xml.dom.minidom.parseString(processed_xml)
                                    pretty_xml = dom.toprettyxml()
                                    # Opcional: Eliminar líneas en blanco adicionales
                                    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
                                    context['processed_content'] = pretty_xml
                                    request.session['processed_xml'] = pretty_xml  # Cambiar 'processed_content' a 'processed_xml'
                                except Exception as e:
                                    logger.error(f"Error al formatear el XML: {str(e)}")
                                    context['error'] = 'Error al formatear el XML procesado.'
                            else:
                                raise ValueError('No XML content in response')
                        else:
                            error_msg = response.json().get('error', 'Error desconocido en el servidor')
                            raise ValueError(f'Flask server error: {error_msg}')
                            
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        
            except requests.RequestException as e:
                logger.error(f"Network error: {str(e)}")
                context['error'] = f'Error de conexión con el servidor: {str(e)}'
            except ValueError as e:
                logger.error(f"Processing error: {str(e)}")
                context['error'] = f'Error procesando archivo: {str(e)}'
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                context['error'] = f'Error inesperado: {str(e)}'
        else:
            context['error'] = 'Formulario inválido'
            logger.error(f"Form errors: {form.errors}")
    
    return render(request, 'cargar.html', context)



def store_request_data(request, data, request_type):
    if 'requests' not in request.session:
        request.session['requests'] = []
    
    # Add timestamp to the request data
    if isinstance(data, dict):
        data_with_timestamp = data.copy()
    else:
        data_with_timestamp = {'content': data}
    
    data_with_timestamp['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    request.session['requests'].append({
        'type': request_type,
        'data': data_with_timestamp
    })
    request.session.modified = True

def ayuda(request):
    return render(request, 'ayuda.html')

def reset_session(request):
    request.session.flush()
    try:
        response = requests.post(f'{FLASK_API_URL}/reset_session', timeout=30)
        # Opcional: manejar la respuesta o errores
    except Exception as e:
        # Opcional: manejar excepciones
        pass
    return redirect('cargar')

def filtrar_mensajes(request):
    context = {
        'filtered_messages': [],
        'total': 0,
        'positivos': 0,
        'negativos': 0,
        'neutros': 0,
        'empresas': [],
        'error': ''
    }

    # Obtener la lista de empresas desde el backend Flask
    try:
        response = requests.get(f'{FLASK_API_URL}/get_empresas', timeout=30)
        if response.status_code == 200:
            context['empresas'] = response.json().get('empresas', [])
            logger.debug(f"Empresas obtenidas: {context['empresas']}")
        else:
            context['error'] = response.json().get('error', 'Error desconocido en el servidor')
    except requests.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        context['error'] = f'Error de conexión con el servidor: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        context['error'] = f'Error inesperado: {str(e)}'

    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        empresa = request.POST.get('empresa')

        try:
            response = requests.post(
                f'{FLASK_API_URL}/filtrar_mensajes',
                json={'fecha': fecha, 'empresa': empresa},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                context['filtered_messages'] = data.get('filtered_messages', [])
                context['total'] = data.get('total', 0)
                context['positivos'] = data.get('positivos', 0)
                context['negativos'] = data.get('negativos', 0)
                context['neutros'] = data.get('neutros', 0)
            else:
                context['error'] = response.json().get('error', 'Error desconocido en el servidor')

        except requests.RequestException as e:
            logger.error(f"Network error: {str(e)}")
            context['error'] = f'Error de conexión con el servidor: {str(e)}'
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            context['error'] = f'Error inesperado: {str(e)}'

    return render(request, 'fecha.html', context)