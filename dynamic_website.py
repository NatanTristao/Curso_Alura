#Próximas etapas:
 #Criar a tabela company.                                                                               CHECK
    #Cadastrar Adminis                                                                                  CHECK
 #Adicionar novos campos nas tabelas users vinculando o ID da empresa.                                  CHECK
 #Adicionar novos campos nas tabelas uploads, vinculando o ID da empresa.                               CHECK
 #Criar uma tela para cadastro de empresas pelo usuário master.                                         CHECK
 #Ajustar o cadastro de usuários para vincular à empresa correspondente.                                CHECK
 #Ajustar o cadastro de ontologias para associá-las à empresa.                                          CHECK
 #No painel do usuário admin, exibir apenas os usuários da empresa vinculada                            CHECK
 #No painel do usuário admin, exibir apenas as ontologias da empresa vinculada.                         CHECK
 
 #No painel do usuário admin, exibir apenas as imagens da empresa vinculada                             CHECK
 

 #Na tela de visualização de ontologias, exibir apenas aquelas associadas à empresa do usuário logado.  CHECK
 #Criar um diretório de armazenamento para ontologias separado por empresa.                             CHECK
 #Criar um diretorio de armazenamento para imagens, separado por empresa                                CHECK

#Frontend:
 #Ajustar o layout do gerenciamento de ontologias e do cadastro de usuários.                            CHECK
 #Implementar a busca por anotações da classe Thing ou da primeira classe visível.
 #Ajustar o cadastro de usuários permitindo a criação de usuários admin                                 CHECK
 #Criação do cadastro de empresas pelo usuário master                                                   CHECK

#Detalhes
#A edição de usuario não funciona                                                                       CHECK
#TIREI TUDO RELACIONADO A ACHAR IMAGEM (class_page)                                                     CHECK
#Mostrar a ontologia carregada no canto inferior direito                                                CHECK
#Mexer no menu para aparecer a empresa                                                                  CHECK

#Ajustes
#Cadastro de empresa                                                                                    CHECK
#5000/companypage                                                                                       CHECK
#bradcrumbs em create company


from flask import Flask,send_from_directory ,render_template_string, request, redirect, url_for, session, make_response
from owlready2 import *
from datetime import datetime
import sqlite3
import os
import re
import zipfile
from werkzeug.utils import secure_filename

# Inicializa a ontologia - começa com essa ontologia 
ontology_path = "v2.owx"  # Caminho da ontologia inicial
onto = get_ontology(ontology_path).load()

app = Flask(__name__)
app.secret_key = 'mysecretkey'  # Necessária para usar sessões no Flask


app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_ONT_FILES = {'json', 'owl', 'rdf', 'owx'}
ALLOWED_IMAGE_FILES = {'zip'}

DATABASE = 'users.db'

onto = None
loaded_ontologies = []

#-------------------------FUNÇÕES-------------------------#

@app.route('/uploads/<company>/imagens/<filename>')
def uploaded_file(company, filename):
    # Monta o caminho para a subpasta "imagens" dentro da pasta da empresa
    folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(company), 'imagens')
    return send_from_directory(folder, filename)

def add_breadcrumb(name, url):
    """
    Adiciona ou atualiza o breadcrumb na sessão.
    Se o breadcrumb já existir, remove os que vieram depois dele.
    """
    breadcrumbs = session.get('breadcrumbs', [])
    # Verifica se a página já está na trilha
    for i, crumb in enumerate(breadcrumbs):
        if crumb['url'] == url:
            breadcrumbs = breadcrumbs[:i+1]
            session['breadcrumbs'] = breadcrumbs
            return breadcrumbs
    # Se não existir, adiciona no final
    breadcrumbs.append({'name': name, 'url': url})
    session['breadcrumbs'] = breadcrumbs
    return breadcrumbs

def find_image_file(directory, filename):
    """
    Busca recursivamente pelo arquivo 'filename' a partir do diretório 'directory'.
    Retorna o caminho completo se encontrado ou None caso contrário.
    """
    for root, dirs, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None

# Função para verificar extensões de arquivos permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_FILES

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            trade_name TEXT NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            adress TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            contact_email TEXT UNIQUE NOT NULL,
            contact_phone TEXT NOT NULL,
            date_created DATE DEFAULT (DATE('now')),
            status TEXT CHECK(status IN ('Ativo', 'Inativo')) NOT NULL DEFAULT 'Ativo'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            sector TEXT,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            company_id TEXT,
            is_approved INTEGER DEFAULT 0,
            FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE SET NULL
        ) 
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ontology_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ontology_name TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            company_id TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_name TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            company_id TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        INSERT OR IGNORE INTO users (name, login, sector, company_id, password, is_approved, is_admin)
        VALUES ('IESB', 'iesb', 'Administração' ,NULL, '123', 1, 1)
    ''')

    cursor.execute('''
        INSERT OR IGNORE INTO users (name, login, sector,  company_id, password, is_approved, is_admin) 
        VALUES ('Admin', 'admin', 'Administração' ,NULL, '123', 1, 1)
    ''')
    conn.commit()
    conn.close()

def collect_properties_along_path(cls):
    collected_properties = {}
    current_class = cls

    while current_class != Thing: 
        for prop in onto.object_properties():
            values = getattr(current_class, prop.name, [])
            if values:
                if prop.name not in collected_properties:
                    collected_properties[prop.name] = []
                collected_properties[prop.name].extend([v.name for v in values if v.name not in collected_properties[prop.name]])

        if current_class.is_a:
            current_class = current_class.is_a[0] 
        else:
            break

    return collected_properties

#---------------------------------------------------------#    

init_db()  # Chama a função para criar o banco de dados

#@app.route('/', methods=['GET', 'POST'])
#def web_master():
"""Página de início da IESB"""


@app.route('/', methods=['GET', 'POST'])
def login_page():
    """Página de login."""
    

    breadcrumbs = add_breadcrumb("Login", url_for('login_page'))
    login = None
    error_message = None
    session.clear()

    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT login, password, is_admin, company_id FROM users WHERE login = ? AND password = ?', (login, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            
            if user[-1] == 0:  # Supondo que is_approved seja a última coluna
                return redirect(url_for('not_allowed_page'))
            
            session['user_login'] = login
            session['login'] = login
            if user[0] != 'iesb':
                session['company_id'] = user[3]

            is_admin = user[2]

            if login == 'iesb':
                return redirect(url_for('master_user'))
            elif is_admin == 1:
                return redirect(url_for('admin_page'))
            
            return redirect(url_for('ontology_page'))
        else:
            error_message = "Login ou senha incorretos!"

    html = """
    <html>
        <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-pag-login">Página de login</div>

                

            </header>
            <main class="form-container2">
                <form method="POST">
                    <label for="login">Login:</label>
                    <input type="text" id="login" name="login" placeholder="Login" required>

                    <label for="password">Senha:</label>
                    <input type="password" id="password" name="password" placeholder="Senha" required>

                    <button type="submit">Entrar</button>
                </form>

                {% if error_message %}
                <div class="error-message">
                    {{ error_message }}
                </div>
                {% endif %}
                
            </main>
        </body>
    </html>
    """
    return render_template_string(html, login=login ,error_message=error_message,breadcrumbs=breadcrumbs )


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    """Página de cadastro de usuários."""
    if not session.get('login'):
        return redirect(url_for('login_page'))

    error_message = None
    success_message = None

    breadcrumbs = add_breadcrumb("Registro", url_for('register_page'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if session.get('login') == 'iesb':
        cursor.execute("SELECT id, company_name FROM company")
    else:
        # Aqui é importante que, no login do admin, você já armazene o company_id na sessão.
        admin_company_id = session.get('company_id')
        cursor.execute("SELECT id, company_name FROM company WHERE id = ?", (admin_company_id,))
    companies = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        name = request.form['name']
        login = request.form['login']
        sector = request.form['sector']
        company_id = request.form['company_id']  # Nome da empresa escolhida
        password = request.form['password']

        if len(password) < 8:
            error_message = "A senha deve conter no mínimo 8 caracteres."

        elif not re.fullmatch(r'[A-Za-zÀ-ÖØ-öø-ÿ ]+', name):
            error_message = "O nome deve conter apenas letras."

        elif not re.search(r'[^A-Za-z0-9]', password):
            error_message = "A senha deve conter pelo menos um caractere especial."

        elif not re.search(r'[A-Z]', password):
            error_message = "A senha deve conter pelo menos uma letra maiúscula."

        else:    
            try:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()

                # Inserir usuário vinculando ao company_id selecionado
                cursor.execute(
                    "INSERT INTO users (name, login, sector, company_id, password) VALUES (?, ?, ?, ?, ?)",
                    (name, login, sector, company_id, password),
                )
                conn.commit()
                conn.close()
                success_message = "Usuário registrado com sucesso!"
            except sqlite3.IntegrityError:
                error_message = "Login já está em uso. Escolha outro."

    html = """
        <html>
        <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-pag-login">Página de Cadastro</div>

                <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

            </header>
            <main class="form-container2">
            <form method="POST">
                <label for="name">Nome:</label>
                <input type="text" id="name" name="name" placeholder="Nome" required><br>

                <label for="login">Login:</label>
                <input type="text" id="login" name="login" placeholder="Login" required><br>

                <label for="sector">Setor:</label>
                <input type="text" id="sector" name="sector" placeholder="Setor" required><br>


                <label for="company_id">Empresa:</label>
                <select id="company_id" name="company_id" required>
                    <option value="" disabled selected>Selecione a empresa</option>
                    {% for company in companies %}
                        <option value="{{ company[0] }}">{{ company[1] }}</option>
                    {% endfor %}
                </select><br>

                <label for="password">Senha:</label>
                <input type="password" id="password" name="password" placeholder="Senha de 8 caracteres" required><br>

                <button type="submit">Registrar</button>
            </form>
            {% if error_message %}
            <div style="color: red;">{{ error_message }}</div>
            {% endif %}
            {% if success_message %}
            <div style="color: green;">{{ success_message }}</div>
            {% endif %}
            </main>
        </body>
        </html>
    """
    return render_template_string(html, error_message=error_message,breadcrumbs=breadcrumbs ,success_message=success_message, companies=companies)

@app.route('/ontology', methods=['GET', 'POST'])
#@login_required
def ontology_page():
    """Página principal da ontologia."""
    if not session.get('login'):
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Ontologia", url_for('ontology_page'))


    root_classes = list({(cls.iri, cls.name) for cls in Thing.subclasses()})
    user_login = session.get('user_login', 'Usuário desconhecido') 

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT users.sector, company.company_name, users.is_approved
        FROM users
        LEFT JOIN company ON users.company_id = company.id
        WHERE users.login = ?
    ''', (user_login,))


    user_status = cursor.fetchone()
    conn.close()
    
    # Define o nome da ontologia com base na lista de ontologias carregadas.
     #Se houver pelo menos uma ontologia, usa o nome da última carregada; senão exibe uma mensagem padrão.
    if loaded_ontologies:
        ontology_filename = loaded_ontologies[-1]['name']
        ontology_name = os.path.splitext(ontology_filename)[0]
    else:
        ontology_name = onto


    # Verifica se o usuário existe e está aprovado
    if not user_status:
        return "Usuário não encontrado.", 404

    sector, company, is_approved = user_status

    if is_approved == 0:
        return redirect(url_for('not_allowed_page'))

    sector = sector if sector else 'Não informado'
    company = company if company else 'Não informado'

    html = """
    <html>
        <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <header>
                
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Bem-vindo, {{ login }}</div>

                <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>


                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>                
            </header>

             
    

            <div class="sidebar">

            <button class="sidebar__toggle" type="button" aria-label="Toggle sidebar"></button>

            <ul class="sidebar__navigation sidebar-navigation">

                <li class="sidebar-navigation__item">
                    <i class="fas fa-user"></i>
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Login: </strong>{{ login }}</a>
                </li>

                <li class="sidebar-navigation__item">
                    <i class="fas fa-briefcase"></i>
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Setor: </strong>{{ sector }}</a>
                </li>

                <li class="sidebar-navigation__item">
                    <i class="fas fa-building"></i>
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Empresa: </strong>{{ company }}</a>
                </li>

                <li class="sidebar-navigation__item">
    
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Ontologia Carregada: </strong> {{ ontology_name }}</a>
                </li>

            </ul>

            </div>

            <script type="text/javascript">
            var toggleBtn = document.querySelector('.sidebar__toggle');
            var sidebar = document.querySelector('.sidebar');

            toggleBtn.addEventListener('click', clickToggleBtnHandler);

            function clickToggleBtnHandler() {
                sidebar.classList.toggle('sidebar--active');
            }
            </script>

            <main class="container">
               
                <ul>
                    {% for class_iri, class_name in root_classes %}
                        <li><a href="{{ url_for('class_page', iri=class_iri) }}">{{ class_name }}</a></li>
                    {% endfor %}
                </ul>
            </main>
        </body>
    </html>
    """
    return render_template_string(html, breadcrumbs=breadcrumbs ,root_classes=root_classes,ontology_name=ontology_name ,loaded_ontologies=loaded_ontologies, login=user_login, sector=sector,company=company)

@app.route('/class/<path:iri>')
def class_page(iri):
    """Página de detalhes de uma classe."""
    if not session.get('login'):
        return redirect(url_for('login_page'))

    global onto

    # Conexão com o banco de dados
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Obtém o login do usuário
    user_login = session.get('user_login', None)
    if not user_login:
        conn.close()
        return "Erro: Usuário não autenticado.", 401

    # Busca a empresa associada ao usuário
    cursor.execute('SELECT company_id FROM users WHERE login = ?', (user_login,))
    company_data = cursor.fetchone()

    if not company_data or not company_data[0]:
        conn.close()
        return "Erro: Usuário não está vinculado a nenhuma empresa.", 403

    company_id = company_data[0]

    # Obtém o nome da empresa
    cursor.execute('SELECT company_name FROM company WHERE id = ?', (company_id,))
    company_name_data = cursor.fetchone()
    if not company_name_data:
        conn.close()
        return "Erro: Empresa não encontrada.", 500
    company_name = company_name_data[0]

    # Obtém o nome da ontologia mais recente associada à empresa
    cursor.execute('''
        SELECT ontology_name FROM ontology_uploads
        WHERE company_id = ?
        ORDER BY upload_date DESC LIMIT 1
    ''', (company_id,))
    ontology_entry = cursor.fetchone()
    conn.close()

    if not ontology_entry:
        return "Erro: Nenhuma ontologia encontrada para esta empresa.", 404

    ontology_filename = ontology_entry[0]
    # Monta o caminho usando a subpasta da empresa
    ontology_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(company_name),"ontologias", ontology_filename)

    # Verifica se o arquivo da ontologia existe
    if not os.path.exists(ontology_path):
        return f"Erro: O arquivo da ontologia '{ontology_filename}' não foi encontrado.", 500

    # Carregar a ontologia se necessário
    if onto is None or onto.name != ontology_filename:
        onto = get_ontology(f"file://{ontology_path}").load()

    # Verifica se a ontologia realmente foi carregada e contém classes
    if not onto.classes():
        return "Erro: A ontologia está vazia ou não foi carregada corretamente.", 500

    # Busca a classe pela IRI
    classes_found = onto.search(iri=iri)
    if not classes_found:
        return "Classe não encontrada", 404

    Class = classes_found[0]

    html = """
    <html>
        <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Bem-vindo, {{ login }}</div>

                <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
                
            </header>

            <div class="ontology-loaded">
                <strong>Ontologia Carregada:</strong> {{ ontology_name }}
            </div>
            <div class="sidebar">

            <button class="sidebar__toggle" type="button" aria-label="Toggle sidebar"></button>

            <ul class="sidebar__navigation sidebar-navigation">

                <li class="sidebar-navigation__item">
                    <i class="fas fa-user"></i>
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Login: </strong>{{ login }}</a>
                </li>

                <li class="sidebar-navigation__item">
                    <i class="fas fa-briefcase"></i>
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Setor: </strong>{{ sector }}</a>
                </li>

                <li class="sidebar-navigation__item">
                    <i class="fas fa-building"></i>
                    <a class="sidebar-navigation__link" href="#" title="Formulários"><strong>Empresa: </strong>{{ company }}</a>
                </li>

            </ul>

            </div>

            <script type="text/javascript">
            var toggleBtn = document.querySelector('.sidebar__toggle');
            var sidebar = document.querySelector('.sidebar');

            toggleBtn.addEventListener('click', clickToggleBtnHandler);

            function clickToggleBtnHandler() {
                sidebar.classList.toggle('sidebar--active');
            }
            </script>

            <main class="container">
                <div class="column">
                    <h2>{{ class_name }}</h2>
                    <div class="path">
                        <h3>Caminho</h3>
                        <div>
                            {% for super_name in superclasses %}
                                <div class="class-item">{{ super_name }}</div>
                            {% endfor %}
                        </div>
                    </div>
                    <h3>Subclasses</h3>
                    <ul>
                        {% for sub_iri, sub_name in subclasses %}
                            <li><a href="{{ url_for('class_page', iri=sub_iri) }}">{{ sub_name }}</a></li>
                        {% endfor %}
                    </ul>
                </div>
                <div class="column">
                    <h3>Anotações</h3>
                    <ul>
                {% if annotations %}
                    {% for key, value in annotations.items() %}
                        {% if value.endswith('.png') or value.endswith('.jpg') or value.endswith('.jpeg') or value.endswith('.gif') %}
                                    <li>
                                        <strong>{{ key }}</strong>: 
                                        <a href="{{ url_for('uploaded_file', company=company, filename=value) }}" target="_blank">
                                            {{ value }}
                                        </a>
                                    </li>
                                {% elif value.startswith('http://') or value.startswith('https://') %}
                                    <li>
                                        <strong>{{ key }}</strong>: 
                                        <a href="{{ value }}" target="_blank">{{ value }}</a>
                                    </li>
                                {% else %}
                                    <li><strong>{{ key }}</strong>: {{ value }}</li>
                                {% endif %}
                            {% endfor %}
                        {% else %}
                            <li>Nenhuma anotação encontrada.</li>
                        {% endif %}
                    </ul>
                    <h3>Descrição</h3>
                    <ul>
                        {% if object_properties %}
                            {% for key, values in object_properties.items() %}
                                {% for value in values %}
                                    <li>
                                        <strong>{{ key }}</strong>: {{ value }}
                                    </li>
                                {% endfor %}
                            {% endfor %}
                        {% elif all_properties %}
                                {% for key, values in all_properties.items() %}
                                    {% for value in values %}
                                        <li>
                                            <strong>{{ key }}</strong>: {{ value }}
                                        </li>
                                    {% endfor %}
                            {% endfor %}
                        {% else %}
                            <li>Nenhuma descrição encontrada.</li>
                        {% endif %}
                    </ul>
                </div>
            </main>
        </body>
    </html>
    """

     # Obtém anotações da classe atual, removendo duplicatas
    annotations = {}
    for prop in onto.annotation_properties():
        values = getattr(Class, prop.name, [])
        if values:
            # Remove duplicatas preservando a ordem
            unique_values = list(dict.fromkeys(values))
            annotations[prop.name] = ", ".join(str(v) for v in unique_values)

    # Procura pela imagem associada via propriedade "temImage"
    image_filename = None
    for prop in onto.annotation_properties():
        if prop.name == "temImage":
            values = getattr(Class, prop.name, [])
            if values:
                image_filename = values[0]  # Pega a primeira imagem associada
                break

    image_url_final = None
    if image_filename:
        # Monta o caminho do arquivo da imagem na subpasta "imagens"
        image_fs_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            secure_filename(company_name),
            "imagens",
            image_filename
        )
        # Verifica se o arquivo da imagem existe
        if os.path.exists(image_fs_path):
            # Gera a URL usando a rota que serve os arquivos (ex: 'uploaded_file')
            image_url_final = url_for(
                'uploaded_file',
                filename=os.path.join(secure_filename(company_name), "imagens", image_filename)
            )
        else:
            print(f"Imagem não encontrada em: {image_fs_path}")

    # Superclasses (exemplo simplificado)
    superclasses = []
    current_class = Class
    while current_class != Thing:
        for super_class in current_class.is_a:
            superclasses.append(super_class.name)
            current_class = super_class
            break

    # Obtém as subclasses da classe atual, evitando duplicatas
    subclasses = []
    for sub in Class.subclasses():
        tup = (sub.iri, sub.name)
        if tup not in subclasses:
            subclasses.append(tup)

    all_properties = collect_properties_along_path(Class)

    object_properties = {}
    for prop in onto.object_properties():
        values = getattr(Class, prop.name, [])
        if values:
            # Remove duplicatas, se houver
            unique_obj_values = list(dict.fromkeys([v.name for v in values]))
            object_properties[prop.name] = unique_obj_values

    return render_template_string(html, class_name=Class.name,company=company_name ,image_url_final=image_url_final,ontology_name=ontology_filename ,all_properties = all_properties, object_properties=object_properties, annotations=annotations,superclasses=superclasses, subclasses=subclasses,   login=user_login)


@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    """Página de administração."""
    if not session.get('login'):
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Admin", url_for('admin_page'))


    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    global onto, loaded_ontologies
    user_login = session.get('user_login', 'Usuário desconhecido')

    error_message = None
    success_message = None

    # Processa os formulários
    if request.method == 'POST':
        # Aprovar usuário
        if 'user_id' in request.form and 'is_approved' in request.form:
            user_id = request.form.get('user_id')
            try:
                cursor.execute('UPDATE users SET is_approved = 1 WHERE id = ?', (user_id,))
                conn.commit()
                success_message = f"Usuário com ID {user_id} aprovado com sucesso!"
            except Exception as e:
                error_message = f"Erro ao aprovar usuário: {str(e)}"

        

        # Outras lógicas (importar ou excluir ontologias)
        elif 'import_ontology' in request.form:
            file = request.files.get('ontology_file')
            if file:
                file_path = f"{file.filename}"
                try:
                    file.save(file_path)

                    # Carregar nova ontologia
                    new_world = World()
                    new_onto = new_world.get_ontology(file_path).load()
                    loaded_ontologies.append({
                        'name': file.filename,
                        'upload_time': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                        'path': user_login
                    })
                    onto = new_onto
                    success_message = "Ontologia importada com sucesso!"
                except Exception as e:
                    error_message = f"Erro ao carregar ontologia: {str(e)}"

        elif 'delete_ontology' in request.form:
            ontology_name = request.form.get('ontology_name')
            if ontology_name:
                for i, entry in enumerate(loaded_ontologies):
                    if entry['name'] == ontology_name:
                        try:
                            loaded_ontologies.pop(i)
                            success_message = f"Ontologia '{ontology_name}' removida com sucesso!"
                            break
                        except Exception as e:
                            error_message = f"Erro ao excluir ontologia: {str(e)}"
                            break
                else:
                    error_message = f"Ontologia '{ontology_name}' não encontrada."

        elif 'user_id' in request.form and 'delete_user' in request.form:
            user_id = request.form.get('user_id')
            try:
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                success_message = f"Usuário com ID {user_id} excluído com sucesso!"
            except Exception as e:
                error_message = f"Erro ao excluir usuário: {str(e)}"

    # Recupera usuários aprovados
    cursor.execute('SELECT id, name, login, sector FROM users WHERE login != "admin"')
    users = cursor.fetchall()

    # Recupera usuários pendentes de aprovação
    cursor.execute('SELECT id, name, login FROM users WHERE is_approved = 0')
    pending_users = cursor.fetchall()

    conn.close()

    html = """
    <html>
    <head>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        <header>
            <img src="/static/LOGO_IESB.png" alt="Logo">
            <div class="header-login">Painel de Administrador - Bem-vindo, {{ login }}</div>

            <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

            <a href="{{ url_for('logout') }}">
                <button class="logout-button">Sair</button>
            </a>
        </header>
            <div class="ontology-loaded">
                <p>Bem-vindo ao painel de administrador, aqui você pode gerenciar ontologias e usuários. Clique em uma das seções abaixo para acessar as funcionalidades específicas.</p>
            </div>
        <main class="container">

            <div class="admin-sections">
                <a href="{{ url_for('ontology_manager_page') }}" class="admin-box">
                    <h3>Gerenciar Ontologias</h3>
                </a>
                <a href="{{ url_for('user_manager_page') }}" class="admin-box">
                    <h3>Gerenciar Usuários</h3>
                </a>
            </div>
        </main>
    </body>
</html>

    """
    return render_template_string(html, pending_users=pending_users , login=user_login, breadcrumbs=breadcrumbs ,loaded_ontologies=loaded_ontologies, error_message=error_message, success_message=success_message, users=users)

@app.route('/ontologyManager', methods=['GET', 'POST'])
def ontology_manager_page():
    '''Página administrada pelo admin'''
    if not session.get('login'):
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Admin - Ontologia", url_for('ontology_manager_page'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    
    user_login = session.get('user_login', 'Usuário desconhecido')

    error_message = None
    success_message = None

    # Buscar empresa do usuário logado
    cursor.execute('SELECT company_id FROM users WHERE login = ?', (user_login,))
    company_data = cursor.fetchone()
    
    if not company_data or not company_data[0]:  
        return "Erro: Usuário não associado a nenhuma empresa.", 403

    company_id = company_data[0]  # ID da empresa do usuário logado
    cursor.execute('SELECT company_name FROM company WHERE id = ?', (company_id,))
    company_name_data = cursor.fetchone()

    if not company_name_data:
        return "Erro: Empresa não encontrada.", 403

    company_name = company_name_data[0]
    company_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(company_name))
    ontologies_folder = os.path.join(company_folder, 'ontologias')
    images_folder = os.path.join(company_folder, 'imagens')
    os.makedirs(ontologies_folder, exist_ok=True)
    os.makedirs(images_folder, exist_ok=True)

    # Processa os formulários
    if request.method == 'POST':
        # Aprovar usuário
        if 'user_id' in request.form and 'is_approved' in request.form:
            user_id = request.form.get('user_id')
            try:
                cursor.execute('UPDATE users SET is_approved = 1 WHERE id = ?', (user_id,))
                conn.commit()
                success_message = f"Usuário com ID {user_id} aprovado com sucesso!"
            except Exception as e:
                error_message = f"Erro ao aprovar usuário: {str(e)}"

        # Importação de ontologia
        if 'import_ontology' in request.form:
            file = request.files.get('ontology_file')
            if file:
                file_path = os.path.join(ontologies_folder, secure_filename(file.filename))
                file.save(file_path)
                cursor.execute('''INSERT INTO ontology_uploads (ontology_name, upload_date, uploaded_by, company_id)
                                  VALUES (?, ?, ?, ?)''', (file.filename, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_login, company_id))
                conn.commit()
                success_message = "Ontologia importada com sucesso!"


    if 'import_images' in request.form:
            file = request.files.get('images_folder')
            if file:
                temp_zip_path = os.path.join(images_folder, secure_filename(file.filename))
                try:
                    file.save(temp_zip_path)
                    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(images_folder)
                    os.remove(temp_zip_path)
                    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    for image in os.listdir(images_folder):
                        cursor.execute('''INSERT INTO images_uploads (image_name, upload_date, uploaded_by, company_id)
                                          VALUES (?, ?, ?, ?)''', (image, upload_date, user_login, company_id))
                    conn.commit()
                    success_message = "Imagens importadas com sucesso!"
                except Exception as e:
                    error_message = f"Erro ao importar imagens: {str(e)}"

        # Exclusão de ontologia
    elif 'delete_ontology' in request.form:
            ontology_id = request.form.get('ontology_id')
            ontology_name = request.form.get('ontology_name')
            if ontology_id and ontology_name:
                try:
                    ontology_path = os.path.join(ontologies_folder, ontology_name)
                    if os.path.exists(ontology_path):
                        os.remove(ontology_path)
                    cursor.execute('DELETE FROM ontology_uploads WHERE id = ?', (ontology_id,))
                    conn.commit()
                    success_message = f"Ontologia '{ontology_name}' removida com sucesso!"
                except Exception as e:
                    error_message = f"Erro ao excluir ontologia: {str(e)}"

    elif 'delete_image' in request.form:
            image_id = request.form.get('image_id')
            image_name = request.form.get('image_name')
            if image_id and image_name:
                try:
                    image_path = os.path.join(images_folder, image_name)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    cursor.execute('DELETE FROM images_uploads WHERE id = ?', (image_id,))
                    conn.commit()
                    success_message = f"Imagem '{image_name}' removida com sucesso!"
                except Exception as e:
                    error_message = f"Erro ao excluir imagem: {str(e)}"

    # Buscar apenas os uploads da empresa do usuário logado
    cursor.execute('''
        SELECT id, ontology_name, upload_date, uploaded_by 
        FROM ontology_uploads 
        WHERE company_id = ? 
        ORDER BY upload_date DESC
    ''', (company_id,))
    ontology_uploads = cursor.fetchall()

    cursor.execute('SELECT id, ontology_name, upload_date, uploaded_by FROM ontology_uploads WHERE company_id = ? ORDER BY upload_date DESC', (company_id,))
    ontology_uploads = cursor.fetchall()
    cursor.execute('SELECT id, image_name, upload_date, uploaded_by FROM images_uploads WHERE company_id = ? ORDER BY upload_date DESC', (company_id,))
    images_uploads = cursor.fetchall()
    conn.close()

    html = """
    <html>
        <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Painel de Administrador - Bem-vindo, {{ login }}</div>

                <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
                
            </header>

            <main class="container-admin">
            

                <h2>Importar Ontologia</h2>
                
                
                <div class="import-section">
                    <form action="{{ url_for('ontology_manager_page') }}" method="POST" enctype="multipart/form-data">
                        <label for="ontology_file">Arquivo de Ontologia (.json, .owl, etc.):</label>
                        <input type="file" id="ontology_file" name="ontology_file" accept=".json, .owl, .rdf, .owx">
                        <button type="submit" name="import_ontology">Importar Ontologia</button>
                    </form>
                </div>

                <div class="import-section">
                    <form action="{{ url_for('ontology_manager_page') }}" method="POST" enctype="multipart/form-data">
                        <label for="images_folder">Pasta de Imagens (ZIP):</label>
                        <input type="file" id="images_folder" name="images_folder" accept=".zip">
                        <button type="submit" name="import_images">Importar Imagens</button>
                    </form>
                </div>

                <h3>Uploads de Ontologias</h3>
                <div class="ontology-section">
                    <table border="1">
                        <tr>
                            <th>Nome da Ontologia</th>
                            <th>Data do Upload</th>
                            <th>Usuário</th>
                            <th>Ação</th>
                        </tr>
                        {% for ontology in ontology_uploads %}
                        <tr>
                            <td>{{ ontology[1] }}</td>
                            <td>{{ ontology[2] }}</td>
                            <td>{{ ontology[3] }}</td>
                            <td>
                                <form method="POST">
                                    <input type="hidden" name="ontology_id" value="{{ ontology[0] }}">
                                    <input type="hidden" name="ontology_name" value="{{ ontology[1] }}">
                                    <button type="submit" name="delete_ontology">Excluir</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>

                {% if error_message %}
                <div class="error-message">{{ error_message }}</div>
                {% endif %}
                {% if success_message %}
                <div class="success-message">{{ success_message }}</div>
                {% endif %}

                <h3>Uploads de Imagens</h3>
                <div class="ontology-section">
                    <table border="1">
                        <tr>
                            <th>Nome da Imagem</th>
                            <th>Data do Upload</th>
                            <th>Usuário</th>
                            <th>Excluir</th>
                        </tr>
                        {% for image in images_uploads %}
                        <tr>
                            <td>{{ image[1] }}</td>
                            <td>{{ image[2] }}</td>
                            <td>{{ image[3] }}</td>
                            <td>
                                <form method="POST">
                                    <input type="hidden" name="image_id" value="{{ image[0] }}">
                                    <input type="hidden" name="image_name" value="{{ image[1] }}">
                                    <button type="submit" name="delete_image">Excluir</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>

            </main>
        </body>
    </html>
    """
    return render_template_string(html, login=user_login, ontology_uploads=ontology_uploads, images_uploads=images_uploads ,breadcrumbs=breadcrumbs,error_message=error_message, success_message=success_message)


@app.route('/userManager', methods=['GET', 'POST'])
def user_manager_page():
    '''Página administrada pelo admin'''

    if not session.get('login'):
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Admin - Usuário", url_for('user_manager_page'))


    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    
    user_login = session.get('user_login', 'Usuário desconhecido')

    error_message = None
    success_message = None

    cursor.execute('SELECT company_id FROM users WHERE login = ?', (user_login,))
    admin_company = cursor.fetchone()

    admin_company_id = admin_company[0]

    if request.method == 'POST':
        if 'user_id' in request.form and 'is_approved' in request.form:
            user_id = request.form.get('user_id')
            print(f"Aprovando usuário com ID: {user_id}")  # Debug
            try:
                cursor.execute('UPDATE users SET is_approved = 1 WHERE id = ?', (user_id,))
                if cursor.rowcount == 0:
                    error_message = "Nenhum usuário encontrado com esse ID."
                else:
                    conn.commit()
                    success_message = f"Usuário com ID {user_id} aprovado com sucesso!"
            except Exception as e:
                error_message = f"Erro ao aprovar usuário: {str(e)}"

        elif 'user_id' in request.form and 'delete_user' in request.form:
            user_id = request.form.get('user_id')  # Corrigindo: definir user_id para exclusão
            try:
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                success_message = f"Usuário com ID {user_id} excluído com sucesso!"
            except Exception as e:
                error_message = f"Erro ao excluir usuário: {str(e)}"

        elif 'user_id' in request.form and 'reset_password' in request.form:
            user_id = request.form.get('user_id')
            default_password = "12345"

            try:
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (default_password, user_id))
                conn.commit()
                success_message = f"Senha do usuário com ID {user_id} resetada para {default_password} com sucesso!"
            except Exception as e:
                error_message = f"Erro ao resetar senha: {str(e)}"

    cursor.execute('''
        SELECT users.id, users.name, users.login, users.sector, users.company_id, company.company_name
        FROM users
        LEFT JOIN company ON users.company_id = company.id
        WHERE users.company_id = ? AND users.login != "admin"
    ''', (admin_company_id,))
    users = cursor.fetchall()

    # Recupera usuários pendentes de aprovação
    cursor.execute('''
        SELECT users.id, users.name, users.login, company.company_name
        FROM users
        LEFT JOIN company ON users.company_id = company.id
        WHERE users.is_approved = 0 AND users.company_id = ? AND users.is_admin = 0
    ''', (admin_company_id,))
    pending_users = cursor.fetchall()

    conn.close()
    html = """
    <html>

    <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Painel de Administrador - Bem-vindo, {{ login }}</div>

                 <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
            <main class="container">
                <h2>Usuários cadastrados:</h2>

                <table border="1">
                    <tr>
                        <th>ID</th>
                        <th>Nome</th>
                        <th>Login</th>
                        <th>Setor</th>
                        <th>ID da Empresa</th>
                        <th>Nome Empresa</th>
                        <th>Ações</th>
                    </tr>
                    {% for user in users %}
                    <tr>
                        <td>{{ user[0] }}</td>
                        <td>{{ user[1] }}</td>
                        <td>{{ user[2] }}</td>
                        <td>{{ user[3] }}</td>
                        <td>{{ user[4] if user[4] else 'Sem ID' }}</td>
                        <td>{{ user[5] }}</td>
                        <td>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="user_id" value="{{ user[0] }}">
                                <button type="submit" name="delete_user">Excluir</button>
                            </form>
                            <a href="{{ url_for('edit_user', user_id=user[0]) }}">
                                <button>Editar</button>
                            </a>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="user_id" value="{{ user[0] }}">
                                <button type="submit" name="reset_password">Resetar Senha</button>
                            </form>
                            <a href="{{ url_for('change_password', user_id=user[0]) }}">
                                <button>Alterar Senha</button>
                            </a>

                        </td>
                    </tr>
                    {% endfor %}
                </table>
                
                <h2>Usuários Pendentes de Aprovação:</h2>
                    <table border="1">
                        <tr>
                            <th>ID</th>
                            <th>Nome</th>
                            <th>Login</th>
                            <th>Ação</th>
                        </tr>
                        {% for user in pending_users %}
                        <tr>
                            <td>{{ user[0] }}</td>
                            <td>{{ user[1] }}</td>
                            <td>{{ user[2] }}</td>
                            <td>
                                <form method="POST" style="display: inline;">
                                    <input type="hidden" name="user_id" value="{{ user[0] }}">
                                    <button type="submit" name="is_approved">Aprovar</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                    <a href="{{ url_for('register_page') }}">
                            <button>Cadastrar usuário</button>
                    </a>
                </div>
                {% if error_message %}
            <div style="color: red;">{{ error_message }}</div>
            {% endif %}
            {% if success_message %}
            <div style="color: green;">{{ success_message }}</div>
            {% endif %}
            </main>
        </body>
    </html>
    """
    return render_template_string(html, pending_users=pending_users , login=user_login, breadcrumbs=breadcrumbs,loaded_ontologies=loaded_ontologies, error_message=error_message, success_message=success_message, users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST']) #apenas admin pode alterar
def edit_user(user_id):
    """Página para editar informações de um usuário."""
    if not session.get('login'):
        return redirect(url_for('login_page'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Obtém os dados do usuário a ser editado
    cursor.execute('SELECT id, name, login, sector FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return "Usuário não encontrado", 404

    if request.method == 'POST':
        # Atualiza as informações do usuário
        name = request.form['name']
        login = request.form['login']
        sector = request.form['sector']

        cursor.execute('''
            UPDATE users
            SET name = ?, login = ?, sector = ?
            WHERE id = ?
        ''', (name, login, sector, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('user_manager_page'))

    conn.close()

    html = """
    <html>
        <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Editar Usuário</div>
                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
            <main class="form-container">
            <form method="POST">
                <label for="name">Nome:</label>
                <input type="text" id="name" name="name" value="{{ user[1] }}" required><br>

                <label for="login">Login:</label>
                <input type="text" id="login" name="login" value="{{ user[2] }}" required><br>

                <label for="sector">Setor:</label>
                <input type="text" id="sector" name="sector" value="{{ user[3] }}" required><br>

                <button type="submit">Salvar Alterações</button>
            </form>
            <a href="{{ url_for('user_manager_page') }}">Voltar</a>
            </main>
        </body>
    </html>
    """
    return render_template_string(html, user=user)

@app.route('/change_password/<int:user_id>', methods=['GET', 'POST'])
def change_password(user_id):
    if not session.get('login'):
        return redirect(url_for('login_page'))

    """Página para alterar apenas a senha de um usuário (apenas admin pode alterar)."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Obtém informações básicas do usuário
    cursor.execute('SELECT id, name, login FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "Usuário não encontrado", 404

    error = None

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password:
            error = "Por favor, insira a nova senha."

        elif new_password != confirm_password:
            error = "As senhas não conferem. Tente novamente."

        elif len(new_password) < 8:
            error = "A senha deve conter no mínimo 8 caracteres."

        elif not re.search(r'[^A-Za-z0-9]', new_password):
            error = "A senha deve conter pelo menos um caractere especial."

        elif not re.search(r'[A-Z]', new_password):
            error = "A senha deve conter pelo menos uma letra maiúscula."

        else:
            try:
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
                conn.commit()
            except Exception as e:
                error = f"Erro ao atualizar senha: {str(e)}"
            finally:
                conn.close()
            
            if not error:
                return redirect(url_for('user_manager_page'))

    conn.close()

    html = """
    <html>
        <head>
            <title>Alterar Senha</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Alterar Senha de {{ user[1] }} ({{ user[2] }})</div>
                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
            <main class="form-container">
                
                <form method="POST">
                    <label for="password">Nova Senha:</label>
                    <input type="password" id="password" name="password" placeholder="Senha de 8 caracteres" required><br>

                    <label for="confirm_password">Confirmar Senha:</label>
                    <input type="password" id="confirm_password" name="confirm_password" placeholder="Confirmar senha de 8 caracteres" required><br>

                    <button type="submit">Alterar Senha</button>
                </form>
                {% if error %}
                    <div class="error-message">{{ error }}</div>
                {% endif %}
                <a href="{{ url_for('user_manager_page') }}">Voltar</a>
            </main>
        </body>
    </html>
    """
    return render_template_string(html, user=user, error=error)

@app.route('/logout')
def logout():
    """Função para sair da sessão."""
    session.clear()  # Limpa todos os dados da sessão
    resp = make_response(redirect(url_for('login_page')))
    resp.delete_cookie('login')  # Remove o cookie de login
    return resp

@app.route('/notAllowed')
def not_allowed_page():
    '''Página quando o usuario ainda nao esta permitido pelo admin'''
    html = """
    <html>
    <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
        <title>Acesso Não Autorizado</title>
            <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login"></div>
                
            </header>
                <div class="not-allowed-container">
                <h2>Acesso não autorizado</h2>
                <p>Aguarde aprovação do administrador.</p>
                <a href="{{ url_for('login_page') }}">
                    <button class="">Voltar para o login</button>
                </a>
            </div>
        </body>
    </html>
    """
    return render_template_string(html)

#----------------APENAS USUARIO MASTER--------------------#

@app.route('/masterUser' , methods=['GET', 'POST'])
def master_user():

    if session.get('login') != 'iesb':
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Iesb", url_for('master_user'))
    #criar admin de estabelecimento e criar o estabelecimento
    html = """
    <html>
    <head>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        <header>
            <img src="/static/LOGO_IESB.png" alt="Logo">
            <div class="header-login">Painel IESB</div>

            <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

            <a href="{{ url_for('logout') }}">
                <button class="logout-button">Sair</button>
            </a>
        </header>
            <div class="ontology-loaded">
                <p>Bem-vindo ao painel IESB, aqui você pode gerenciar estabelecimentos e administradores. Clique em uma das seções abaixo para acessar as funcionalidades específicas.</p>
            </div>
        <main class="container">

            <div class="admin-sections">
                <a href="{{ url_for('company_page') }}" class="admin-box">
                    <h3>Gerenciar Estabelecimentos</h3>
                </a>
                <a href="{{ url_for('admin_page_iesb') }}" class="admin-box">
                    <h3>Gerenciar Administradores</h3>
                </a>
            </div>
        </main>
    </body>
</html>

    """
    return render_template_string(html, loaded_ontologies=loaded_ontologies,breadcrumbs=breadcrumbs)

@app.route('/companyPage', methods=['GET', 'POST'])
def company_page():

    if session.get('login') != 'iesb':
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Iesb - Estabelecimento", url_for('company_page'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, company_name, trade_name, cnpj ,  date_created, status  FROM company")
    company = cursor.fetchall()
    conn.close()

    html = """
    <html>

    <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Painel IESB</div>

                 <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>
            

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
            <main class="container">
                <h2>Estabelecimentos cadastrados:</h2>

                <table border="1">
                    <tr>
                        <th>ID</th>
                        <th>Nome</th>
                        <th>Nome Fantasia</th>
                        <th>CNPJ</th>
                        <th>Data de Criação</th>
                        <th>Status</th>
                        <th>Ações</th>
                    </tr>
                    {% for user in company %}
                    <tr>
                        <td>{{ user[0] }}</td>
                        <td>{{ user[1] }}</td>
                        <td>{{ user[2] }}</td>
                        <td>{{ user[3] }}</td>
                        <td>{{ user[4] }}</td>
                        <td>{{ user[5] }}</td>
                        <td>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="user_id" value="{{ user[0] }}">
                                <button type="submit" name="delete_user">Excluir</button>
                            </form>
                            <a href="{{ url_for('edit_user', user_id=user[0]) }}">
                                <button>Editar</button>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                    <a href="{{ url_for('create_company') }}">
                            <button>Cadastrar estabelecimento</button>
                    </a>
                </div>
                
            </main>
        </body>
    </html>
    """
    return render_template_string(html, company=company, breadcrumbs=breadcrumbs)

@app.route('/createCompany', methods=['GET', 'POST'])
def create_company():
    if 'login' not in session or session.get('login') != 'iesb':
        return redirect(url_for('login_page'))

    error_message = None
    success_message = None

    breadcrumbs = add_breadcrumb("Cadastro", url_for('create_company'))
    # Inicializa as variáveis dos campos com valores padrão vazios (ou com um valor padrão desejado)
    company_name_val = ""
    trade_name_val = ""
    cnpj_val = ""
    adress_val = ""
    contact_name_val = ""
    contact_email_val = ""
    contact_phone_val = ""
    date_created_val = ""
    status_val = "Ativo"  # Valor padrão para o select

    # Se for uma requisição POST
    if request.method == 'POST':
        # Se houver o campo 'login' no formulário, trata-o (caso este trecho seja necessário)
        login_input = request.form.get('login')
        if login_input is not None:
            if login_input == 'iesb':
                session['login'] = 'iesb'
                return redirect(url_for('master_user'))
            else:
                return "Login inválido", 401

        breadcrumbs = add_breadcrumb("Cadastro de Empresa", url_for('create_company'))
        # Armazena os valores enviados para que possam ser reexibidos caso haja erro
        company_name_val = request.form.get('company_name', '')
        trade_name_val = request.form.get('trade_name', '')
        cnpj_val = request.form.get('cnpj', '')
        adress_val = request.form.get('adress', '')
        contact_name_val = request.form.get('contact_name', '')
        contact_email_val = request.form.get('contact_email', '')
        contact_phone_val = request.form.get('contact_phone', '')
        date_created_val = request.form.get('date_created', '')
        status_val = request.form.get('status', 'Ativo')

        # Validações
        if not re.fullmatch(r'\d{14}', cnpj_val):
            error_message = "CNPJ deve conter 14 dígitos numéricos"
        elif not re.fullmatch(r'[A-Za-zÀ-ÖØ-öø-ÿ ]+', contact_name_val):
            error_message = "O nome do contato deve conter apenas letras."
        elif not re.fullmatch(r'\d+', contact_phone_val):
            error_message = "O telefone deve conter apenas números."
        else:
            try:
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO company (company_name, trade_name, cnpj, adress, contact_name, contact_email, contact_phone, date_created, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (company_name_val, trade_name_val, cnpj_val, adress_val, contact_name_val, contact_email_val, contact_phone_val, date_created_val, status_val))
                conn.commit()
                conn.close()
                success_message = "Empresa registrada com sucesso!"
                # Opcional: limpar os campos em caso de sucesso
                company_name_val = ""
                trade_name_val = ""
                cnpj_val = ""
                adress_val = ""
                contact_name_val = ""
                contact_email_val = ""
                contact_phone_val = ""
                date_created_val = ""
                status_val = "Ativo"
            except sqlite3.IntegrityError:
                error_message = "CNPJ ou e-mail já estão em uso. Escolha outro."

    

    html = """
    <html>
    <head>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Painel IESB</div>

                 <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>
            

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
        <main class="form-container2">
            <form method="POST">
                <label for="company_name">Razão Social:</label>
                <input type="text" id="company_name" name="company_name" placeholder="Razão Social" required value="{{ company_name_val }}"><br>

                <label for="trade_name">Nome Fantasia:</label>
                <input type="text" id="trade_name" name="trade_name" placeholder="Nome Fantasia" required value="{{ trade_name_val }}"><br>

                <label for="cnpj">CNPJ:</label>
                <input type="text" id="cnpj" name="cnpj" placeholder="CNPJ" required value="{{ cnpj_val }}"><br>

                <label for="adress">Endereço:</label>
                <input type="text" id="adress" name="adress" placeholder="Endereço" required value="{{ adress_val }}"><br>

                <label for="contact_name">Nome do contato:</label>
                <input type="text" id="contact_name" name="contact_name" placeholder="Nome do contato" required value="{{ contact_name_val }}"><br>

                <label for="contact_email">E-mail de contato:</label>
                <input type="email" id="contact_email" name="contact_email" placeholder="E-mail de contato" required value="{{ contact_email_val }}"><br>

                <label for="contact_phone">Telefone de contato:</label>
                <input type="tel" id="contact_phone" name="contact_phone" placeholder="Telefone de contato" required 
                       pattern="\d+" inputmode="numeric" value="{{ contact_phone_val }}"><br>


                <label for="date_created">Data de Criação:</label>
                <input type="date" id="date_created" name="date_created" required value="{{ date_created_val }}"><br>

                <label for="status">Status:</label>
                <select id="status" name="status">
                    <option value="Ativo" {% if status_val == 'Ativo' %}selected{% endif %}>Ativo</option>
                    <option value="Inativo" {% if status_val == 'Inativo' %}selected{% endif %}>Inativo</option>
                </select><br>

                <button type="submit">Registrar Empresa</button>
            </form>
            {% if error_message %}
                <div style="color: red;">{{ error_message }}</div>
            {% endif %}
            {% if success_message %}
                <div style="color: green;">{{ success_message }}</div>
            {% endif %}
        </main>
    </body>
    </html>
    """
    return render_template_string(html, error_message=error_message, success_message=success_message,
                                  company_name_val=company_name_val, trade_name_val=trade_name_val,
                                  cnpj_val=cnpj_val, adress_val=adress_val, contact_name_val=contact_name_val,
                                  contact_email_val=contact_email_val, contact_phone_val=contact_phone_val,
                                  date_created_val=date_created_val, status_val=status_val,
                                  breadcrumbs=breadcrumbs)

@app.route('/adminPageIesb')
def admin_page_iesb():

    if session.get('login') != 'iesb':
        return redirect(url_for('login_page'))
    
    breadcrumbs = add_breadcrumb("Iesb - Administradores", url_for('admin_page_iesb'))
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    

    error_message = None
    success_message = None

    if request.method == 'POST':
        # Aprovar usuário

        if 'user_id' in request.form and 'delete_user' in request.form:
            try:
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                success_message = f"Usuário com ID {user_id} excluído com sucesso!"
            except Exception as e:
                error_message = f"Erro ao excluir usuário: {str(e)}"

        elif 'user_id' in request.form and 'reset_password' in request.form:
            user_id = request.form.get('user_id')
            default_password = "12345"

            try:
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (default_password, user_id))
                conn.commit()
                success_message = f"Senha do usuário com ID {user_id} resetada para {default_password} com sucesso!"
            except Exception as e:
                error_message = f"Erro ao resetar senha: {str(e)}"

    cursor.execute('''
        SELECT users.id, users.name, users.login, users.sector, users.company_id, company.company_name
        FROM users
        LEFT JOIN company ON users.company_id = company.id
        WHERE users.is_admin = 1
    ''')
    users = cursor.fetchall()

    html = """
    <html>

    <head>
            <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Painel IESB</div>

                 <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
            <main class="container">
                <h2>Administradores cadastrados:</h2>

                <table border="1">
                    <tr>
                        <th>ID</th>
                        <th>Nome</th>
                        <th>Login</th>
                        <th>Setor</th>
                        <th>ID da Empresa</th>
                        <th>Nome Empresa</th>
                        <th>Ações</th>
                    </tr>
                    {% for user in users %}
                    <tr>
                        <td>{{ user[0] }}</td>
                        <td>{{ user[1] }}</td>
                        <td>{{ user[2] }}</td>
                        <td>{{ user[3] }}</td>
                        <td>{{ user[4] if user[4] else 'Sem ID' }}</td>
                        <td>{{ user[5] }}</td>
                        <td>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="user_id" value="{{ user[0] }}">
                                <button type="submit" name="delete_user">Excluir</button>
                            </form>
                            <a href="{{ url_for('edit_user', user_id=user[0]) }}">
                                <button>Editar</button>
                            </a>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="user_id" value="{{ user[0] }}">
                                <button type="submit" name="reset_password">Resetar Senha</button>
                            </form>
                            <a href="{{ url_for('change_password', user_id=user[0]) }}">
                                <button>Alterar Senha</button>
                            </a>

                        </td>
                    </tr>
                    {% endfor %}
                </table>
                    <a href="{{ url_for('create_admin') }}">
                            <button>Cadastrar administradores</button>
                    </a>
                </div>
                
            </main>
        </body>
    </html>
    """
    return render_template_string(html, users=users, error_message=error_message,success_message=success_message, breadcrumbs=breadcrumbs)

@app.route('/createAdmin', methods=['GET', 'POST'])
def create_admin():
    if session.get('login') != 'iesb':
        return redirect(url_for('login_page'))

    breadcrumbs = add_breadcrumb("Cadastro de Admin", url_for('create_admin'))

    error_message = None
    success_message = None

    # Recupera as empresas para preencher o select
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name FROM company")
    companies = cursor.fetchall()
    conn.close()

    # Variáveis para preservar os dados do formulário
    name_val = ""
    login_val = ""
    sector_val = ""
    company_id_val = ""
    password_val = ""

    if request.method == 'POST':
        # Captura os valores do formulário
        name_val = request.form.get('name', '')
        login_val = request.form.get('login', '')
        sector_val = request.form.get('sector', '')
        company_id_val = request.form.get('company_id', '')
        password_val = request.form.get('password', '')

        # Validações
        if len(password_val) < 8:
            error_message = "A senha deve conter no mínimo 8 caracteres."
        elif not re.fullmatch(r'[A-Za-zÀ-ÖØ-öø-ÿ ]+', name_val):
            error_message = "O nome deve conter apenas letras."
        elif not re.search(r'[^A-Za-z0-9]', password_val):
            error_message = "A senha deve conter pelo menos um caractere especial."
        elif not re.search(r'[A-Z]', password_val):
            error_message = "A senha deve conter pelo menos uma letra maiúscula."
        else:
            try:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (name, login, sector, company_id, password, is_admin)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (name_val, login_val, sector_val, company_id_val, password_val))
                conn.commit()
                conn.close()
                success_message = "Usuário administrador registrado com sucesso!"
                # Opcional: limpar os campos em caso de sucesso
                name_val = ""
                login_val = ""
                sector_val = ""
                company_id_val = ""
                password_val = ""
            except sqlite3.IntegrityError:
                error_message = "Login já está em uso. Escolha outro."

    html = """
    <html>
    <head>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        <header>
                <img src="/static/LOGO_IESB.png" alt="Logo">
                <div class="header-login">Painel IESB</div>

                 <nav>
                <ul class="breadcrumb">
                    {% for crumb in breadcrumbs %}
                        {% if crumb.url %}
                            <li><a href="{{ crumb.url }}">{{ crumb.name }}</a></li>
                        {% else %}
                            <li class="active">{{ crumb.name }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </nav>
            

                <a href="{{ url_for('logout') }}">
                    <button class="logout-button">Sair</button>
                </a>
            </header>
        <main class="form-container">
            <form method="POST">
                <label for="name">Nome:</label>
                <input type="text" id="name" name="name" placeholder="Nome" required value="{{ name_val }}"><br>

                <label for="login">Login:</label>
                <input type="text" id="login" name="login" placeholder="Login" required value="{{ login_val }}"><br>

                <label for="sector">Setor:</label>
                <input type="text" id="sector" name="sector" placeholder="Setor" required value="{{ sector_val }}"><br>

                <label for="company_id">Empresa:</label>
                <select id="company_id" name="company_id" required>
                    <option value="" disabled {% if not company_id_val %}selected{% endif %}>Selecione a empresa</option>
                    {% for company in companies %}
                        <option value="{{ company[0] }}" {% if company_id_val == company[0]|string %}selected{% endif %}>
                            {{ company[1] }}
                        </option>
                    {% endfor %}
                </select><br>

                <label for="password">Senha:</label>
                <input type="password" id="password" name="password" placeholder="Senha de 8 caracteres" required value="{{ password_val }}"><br>

                <button type="submit">Registrar</button>
            </form>
            {% if error_message %}
                <div style="color: red;">{{ error_message }}</div>
            {% endif %}
            {% if success_message %}
                <div style="color: green;">{{ success_message }}</div>
            {% endif %}
        </main>
    </body>
    </html>
    """
    return render_template_string(html, error_message=error_message,
                                  success_message=success_message, companies=companies,
                                  breadcrumbs=breadcrumbs, name_val=name_val, login_val=login_val,
                                  sector_val=sector_val, company_id_val=company_id_val,
                                  password_val=password_val)

#--------------------------------------------------------#
if __name__ == '__main__':
    app.run(host='localhost', port=5000)