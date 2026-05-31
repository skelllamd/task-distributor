"""
Веб-интерфейс системы интеллектуального распределения задач
Запуск: streamlit run app.py
"""
import json
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from core import TaskDistributorCore
import plotly.express as px
import plotly.graph_objects as go

def check_workload_validation(employees, tasks, recommendations):
    """Проверка, не перегружены ли сотрудники"""
    warnings = []
    
    # Проверка по каждому сотруднику
    for _, emp in employees.iterrows():
        # Суммарные трудозатраты назначенных задач
        assigned_hours = recommendations[recommendations['исполнитель'] == emp['name']]['трудозатраты_ч'].sum()
        available = emp['available_hours']
        
        if assigned_hours > available:
            warnings.append({
                'тип': '❌ ПЕРЕГРУЗКА',
                'сотрудник': emp['name'],
                'назначено_часов': assigned_hours,
                'доступно_часов': available,
                'перегрузка': assigned_hours - available
            })
        elif assigned_hours > available * 0.9:
            warnings.append({
                'тип': '⚠️ ВНИМАНИЕ',
                'сотрудник': emp['name'],
                'назначено_часов': assigned_hours,
                'доступно_часов': available,
                'перегрузка': 0
            })
    
    return warnings

def update_employee(emp_id, available_hours):
    """Обновление доступных часов сотрудника"""
    with open('data/employees.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for emp in data['employees']:
        if emp['id'] == emp_id:
            emp['available_hours'] = available_hours
            break
    
    with open('data/employees.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    st.rerun()

def delete_task(task_id):
    """Удаление задачи из tasks.json"""
    with open('data/tasks.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Удаляем задачу
    data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
    
    with open('data/tasks.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    st.rerun()

def add_new_task(title, description, required_skills, estimated_hours, priority, deadline):
    """Добавление новой задачи в tasks.json"""
    import json
    from datetime import datetime
    
    with open('data/tasks.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Генерируем новый ID (максимальный + 1)
    max_id = max([t['id'] for t in data['tasks']]) if data['tasks'] else 100
    new_id = max_id + 1
    
    # Создаём новую задачу
    new_task = {
        "id": new_id,
        "title": title,
        "description": description,
        "required_skills": [s.strip() for s in required_skills.split(',')],
        "estimated_hours": estimated_hours,
        "priority": priority,
        "deadline": deadline
    }
    
    data['tasks'].append(new_task)
    
    with open('data/tasks.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Настройка страницы
st.set_page_config(
    page_title="Система распределения задач",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# Заголовок
st.title("🧠 Система интеллектуального распределения задач")
st.caption("На основе анализа компетенций и загрузки сотрудников")

# Инициализация системы
@st.cache_resource
def init_system():
    return TaskDistributorCore()

system = init_system()

# Загрузка данных
try:
    employees = system.load_employees()
    tasks = system.load_tasks()
    st.success(f"✅ Загружено {len(employees)} сотрудников и {len(tasks)} задач")
except Exception as e:
    st.error(f"Ошибка загрузки данных: {e}")
    st.stop()
# Боковое меню
menu = st.sidebar.radio(
    "Выберите раздел",
    ["📊 Распределение задач", "👥 Сотрудники", "👤 Мои задачи", "📝 Задачи", "📈 Аналитика", "🔄 Сравнение критериев", "📜 История", "⚙️ Настройки"]
)

def add_new_employee(name, role, grade, skills, available_hours, max_hours):
    """Добавление нового сотрудника в employees.json"""
    import json
    
    with open('data/employees.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Генерируем новый ID (максимальный + 1)
    max_id = max([e['id'] for e in data['employees']]) if data['employees'] else 1
    new_id = max_id + 1
    
    # Создаём нового сотрудника
    new_employee = {
        "id": new_id,
        "name": name,
        "role": role,
        "grade": grade,
        "skills": [s.strip() for s in skills.split(',')],
        "available_hours": available_hours,
        "max_hours": max_hours
    }
    
    data['employees'].append(new_employee)
    
    with open('data/employees.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def export_to_excel(recommendations, employees, tasks):
    """Экспорт результатов распределения в Excel"""
    import pandas as pd
    from io import BytesIO
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Лист с рекомендациями
        recommendations.to_excel(writer, sheet_name='Рекомендации', index=False)
        
        # Лист с сотрудниками
        employees_df = employees[['name', 'role', 'grade', 'skills', 'available_hours', 'max_hours']].copy()
        employees_df.to_excel(writer, sheet_name='Сотрудники', index=False)
        
        # Лист с задачами
        tasks_df = tasks[['id', 'title', 'required_skills', 'estimated_hours', 'priority', 'deadline']].copy()
        tasks_df.to_excel(writer, sheet_name='Задачи', index=False)
    
    return output.getvalue()

def compare_criteria(system):
    """Сравнение результатов двух критериев оптимизации"""
    
    # Запускаем первый критерий: Максимум компетенций
    rec_max = system.run_full_pipeline(criterion='max_competency')
    metrics_max = system.calculate_metrics()
    
    # Очищаем назначения перед вторым запуском
    system.assignment = None
    
    # Запускаем второй критерий: Сбалансированная загрузка
    rec_balanced = system.run_full_pipeline(criterion='balanced')
    metrics_balanced = system.calculate_metrics()
    
    return rec_max, metrics_max, rec_balanced, metrics_balanced

def save_to_history(recommendations, criterion):
    """Сохранение результатов распределения в историю"""
    import json
    from datetime import datetime
    
    history_file = 'history.json'
    
    # Загружаем существующую историю
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    
    # Создаём запись о распределении
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "criterion": criterion,
        "criterion_name": "Максимум компетенций" if criterion == "max_competency" else "Сбалансированная загрузка",
        "assignments": recommendations.to_dict(orient='records')
    }
    
    history.append(record)
    
    # Сохраняем обратно
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    return len(history)


def load_history():
    """Загрузка истории распределений"""
    import json
    
    history_file = 'history.json'
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def create_gantt_chart(recommendations, employees, tasks):
    """Создание диаграммы Ганта для визуализации распределения задач"""
    import plotly.express as px
    import pandas as pd
    from datetime import datetime, timedelta
    
    gantt_data = []
    start_date = datetime.now()
    
    for _, rec in recommendations.iterrows():
        task = tasks[tasks['id'] == rec['id_задачи']].iloc[0]
        hours = rec['трудозатраты_ч']
        end_date = start_date + timedelta(hours=hours/8)  # 8 часов = 1 рабочий день
        
        gantt_data.append({
            'Задача': rec['задача'][:30],
            'Исполнитель': rec['исполнитель'],
            'Начало': start_date,
            'Конец': end_date,
            'Трудозатраты (ч)': hours,
            'Совместимость (%)': rec['совместимость_%']
        })
        start_date = end_date + timedelta(hours=1)  # небольшой промежуток между задачами
    
    df = pd.DataFrame(gantt_data)
    
    fig = px.timeline(
        df, 
        x_start="Начало", 
        x_end="Конец", 
        y="Исполнитель",
        color="Совместимость (%)",
        text="Задача",
        title="Диаграмма Ганта — Распределение задач по времени",
        color_continuous_scale="Viridis"
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(textposition="inside", insidetextanchor="middle")
    
    return fig

def load_assigned_tasks():
    """Загрузка списка уже назначенных задач"""
    import json
    try:
        with open('assigned_tasks.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_assigned_tasks(assigned):
    """Сохранение списка назначенных задач"""
    import json
    with open('assigned_tasks.json', 'w', encoding='utf-8') as f:
        json.dump(assigned, f, ensure_ascii=False, indent=2)

def distribute_only_new_tasks(system, criterion='max_competency'):
    """Распределение только новых (ещё не назначенных) задач"""
    import json
    from datetime import datetime
    import pandas as pd
    
    # Перезагружаем задачи из файла
    system.load_tasks()
    
    # Загружаем уже назначенные задачи
    assigned = load_assigned_tasks()
    
    # Получаем ID уже назначенных задач
    assigned_ids = set(assigned.keys())
    
    # Фильтруем только новые задачи (которых нет в assigned)
    all_tasks = system.tasks.copy()
    new_tasks = all_tasks[~all_tasks['id'].astype(str).isin(assigned_ids)]
    
    if len(new_tasks) == 0:
        return None, "Нет новых задач для распределения"
    
    # Сохраняем старые назначения для отображения
    old_recommendations = []
    for task_id, info in assigned.items():
        task = all_tasks[all_tasks['id'] == int(task_id)]
        if len(task) > 0:
            old_recommendations.append({
                'id_задачи': int(task_id),
                'задача': task.iloc[0]['title'],
                'исполнитель': info['employee'],
                'совместимость_%': 100.0,
                'трудозатраты_ч': task.iloc[0]['estimated_hours'],
                'доступно_часов': 'уже в работе'
            })
    
    # Временно заменяем tasks только новыми
    original_tasks = system.tasks
    system.tasks = new_tasks
    
    # Запускаем распределение только для новых задач
    system.assignment = None
    recommendations_new = system.run_full_pipeline(criterion=criterion)
    
    # Сохраняем новые назначения
    for _, rec in recommendations_new.iterrows():
        assigned[str(rec['id_задачи'])] = {
            'employee': rec['исполнитель'],
            'assigned_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    save_assigned_tasks(assigned)
    
    # Восстанавливаем все задачи
    system.tasks = original_tasks
    system.assignment = None
    
    # Объединяем старые и новые назначения (без дублей)
    all_recommendations = old_recommendations.copy()
    
    for _, rec in recommendations_new.iterrows():
        all_recommendations.append(rec.to_dict())
    
    result_df = pd.DataFrame(all_recommendations)
    
    # Удаляем возможные дубли по id_задачи (оставляем последнее)
    result_df = result_df.drop_duplicates(subset=['id_задачи'], keep='last')
    
    return result_df, f"Распределено {len(new_tasks)} новых задач"

# ========== РАЗДЕЛ 1: РАСПРЕДЕЛЕНИЕ ЗАДАЧ ==========
if menu == "📊 Распределение задач":
    st.header("🎯 Интеллектуальное распределение задач")
    
    col1, col2 = st.columns(2)
    
    with col1:
        criterion = st.selectbox(
            "Выберите критерий оптимизации",
            ["max_competency", "balanced"],
            format_func=lambda x: "Максимум компетенций" if x == "max_competency" else "Сбалансированная загрузка"
        )
    
    with col2:
        st.write("")
        st.write("")
        run_button = st.button("🚀 Распределить задачи", type="primary", use_container_width=True)
    
    if run_button or st.session_state.get('distributed', False):
        with st.spinner("Выполняется оптимизация..."):
            recommendations = system.run_full_pipeline(criterion=criterion)
            metrics = system.calculate_metrics()
            st.session_state['distributed'] = True
            st.session_state['recommendations'] = recommendations
            
            # Сохраняем в историю
            save_to_history(recommendations, criterion)
            st.success("📜 Результат сохранён в историю!")
        
        # Кнопка экспорта Excel
        excel_data = export_to_excel(recommendations, system.employees, system.tasks)
        st.download_button(
            label="📥 Скачать Excel",
            data=excel_data,
            file_name="распределение_задач.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Метрики эффективности
        st.subheader("📊 Метрики эффективности")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Средняя совместимость", f"{metrics['средняя_совместимость_%']}%")
        with col2:
            st.metric("Мин. совместимость", f"{metrics['минимальная_совместимость_%']}%")
        with col3:
            st.metric("Макс. совместимость", f"{metrics['максимальная_совместимость_%']}%")
        with col4:
            st.metric("Всего задач", metrics['всего_задач_в_системе'])
        
        # Таблица рекомендаций
        st.subheader("📋 Рекомендации по назначению")
        st.dataframe(
            recommendations,
            use_container_width=True,
            column_config={
                "совместимость_%": st.column_config.ProgressColumn(
                    "Совместимость",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            }
        )
        
        # Валидация и уведомления о перегрузке
        st.subheader("⚠️ Проверка загрузки сотрудников")
        
        warnings = check_workload_validation(system.employees, system.tasks, recommendations)
        
        if warnings:
            for w in warnings:
                if w['тип'] == '❌ ПЕРЕГРУЗКА':
                    st.error(f"{w['тип']}: {w['сотрудник']} — назначено {w['назначено_часов']}ч, доступно {w['доступно_часов']}ч (перегрузка {w['перегрузка']}ч)")
                else:
                    st.warning(f"{w['тип']}: {w['сотрудник']} — загружен на {w['назначено_часов']} из {w['доступно_часов']}ч (более 90%)")
        else:
            st.success("✅ Все сотрудники загружены корректно! Перегрузок нет.")
        
        # Тепловая карта компетенций
        st.subheader("🔥 Матрица компетенций")
        
        # Выбор сотрудника для подсветки
        highlight_emp = st.selectbox(
            "Подсветить сотрудника", 
            ["Все"] + system.employees['name'].tolist(),
            key="highlight_employee_select"
        )
        
        fig, ax = plt.subplots(figsize=(10, 6))
        heatmap = sns.heatmap(
            system.competency_matrix,
            annot=True,
            cmap='YlGnBu',
            xticklabels=system.employees['name'],
            yticklabels=system.tasks['title'],
            ax=ax,
            fmt='.2f'
        )
        
        # Подсветка выбранного столбца (сотрудника)
        if highlight_emp != "Все":
            emp_idx = system.employees[system.employees['name'] == highlight_emp].index[0]
            for _, spine in heatmap.spines.items():
                spine.set_visible(False)
            heatmap.axvline(emp_idx, color='red', linewidth=3)
            heatmap.axhline(len(system.tasks), color='red', linewidth=3)
        
        ax.set_xlabel("Сотрудники")
        ax.set_ylabel("Задачи")
        ax.set_title(f"Соответствие компетенций (0-1)" + (f" — подсветка: {highlight_emp}" if highlight_emp != "Все" else ""))
        st.pyplot(fig)
        
        # Диаграмма загрузки
        st.subheader("📊 Загрузка сотрудников")
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        bars = ax2.bar(
            system.employees['name'],
            system.employees['available_hours'],
            color='skyblue',
            edgecolor='navy'
        )
        ax2.axhline(y=40, color='red', linestyle='--', label='Норма (40ч)')
        ax2.set_ylabel("Доступные часы")
        ax2.set_title("Текущая загрузка сотрудников")
        ax2.legend()
        for bar, hours in zip(bars, system.employees['available_hours']):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{hours}ч', ha='center', va='bottom')
        st.pyplot(fig2)
        
        # Диаграмма Ганта
        st.subheader("📅 Диаграмма Ганта")
        with st.spinner("Построение диаграммы Ганта..."):
            gantt_fig = create_gantt_chart(recommendations, system.employees, system.tasks)
            st.plotly_chart(gantt_fig, use_container_width=True)
        st.caption("📌 Диаграмма показывает примерный порядок выполнения задач. Время указано условно от момента старта.")
        
        # ========== РУЧНОЕ ПЕРЕНАЗНАЧЕНИЕ ==========
        st.subheader("✏️ Ручное переназначение")
        st.caption("Если вы не согласны с решением системы, вы можете вручную назначить другого исполнителя")
        
        col_man1, col_man2, col_man3 = st.columns([2, 2, 1])
        
        with col_man1:
            task_to_reassign = st.selectbox(
                "Выберите задачу",
                recommendations['задача'].tolist(),
                key="manual_task"
            )
        
        with col_man2:
            all_employees = system.employees['name'].tolist()
            new_assignee = st.selectbox(
                "Назначить другому сотруднику",
                all_employees,
                key="manual_employee"
            )
        
        with col_man3:
            st.write("")
            st.write("")
            if st.button("🔄 Применить переназначение", key="manual_btn"):
                # Обновляем рекомендации
                recommendations.loc[recommendations['задача'] == task_to_reassign, 'исполнитель'] = new_assignee
                st.session_state['recommendations'] = recommendations
                st.success(f"✅ Задача '{task_to_reassign}' переназначена на {new_assignee}")
                st.rerun()

# ========== РАЗДЕЛ 2: СОТРУДНИКИ ==========
elif menu == "👥 Сотрудники":
    st.header("👥 Команда разработки")
    
    # ПОИСК ПО СОТРУДНИКАМ
    search_emp = st.text_input("🔍 Поиск по имени сотрудника", placeholder="Введите имя...")
    
    employees_df = employees[['name', 'role', 'grade', 'skills', 'available_hours', 'max_hours']].copy()
    
    if search_emp:
        employees_df = employees_df[employees_df['name'].str.contains(search_emp, case=False, na=False)]
        st.caption(f"🔎 Найдено сотрудников: {len(employees_df)}")
    
    st.dataframe(employees_df, use_container_width=True)
    
    # РЕДАКТИРОВАНИЕ ЗАГРУЗКИ СОТРУДНИКА
    st.subheader("✏️ Редактирование загрузки сотрудника")
    
    col1, col2 = st.columns(2)
    with col1:
        emp_to_edit = st.selectbox(
            "Выберите сотрудника", 
            employees['name'].tolist(),
            key="edit_employee_select"
        )
    
    # Получаем текущие часы выбранного сотрудника
    current_hours = int(employees[employees['name'] == emp_to_edit]['available_hours'].iloc[0])
    
    with col2:
        new_hours = st.number_input(
            "Новое значение доступных часов", 
            min_value=0, 
            max_value=50, 
            value=current_hours,
            key="edit_hours_input"
        )
    
    if st.button("💾 Сохранить изменения", key="save_employee_btn"):
        emp_id = employees[employees['name'] == emp_to_edit]['id'].iloc[0]
        update_employee(emp_id, new_hours)
        st.success(f"✅ Загрузка сотрудника '{emp_to_edit}' обновлена с {current_hours} на {new_hours} часов")
        st.rerun()
    
    # ДОБАВЛЕНИЕ НОВОГО СОТРУДНИКА
    with st.expander("➕ Добавить нового сотрудника", expanded=False):
        st.subheader("👤 Новый сотрудник")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("ФИО сотрудника", key="new_name")
            new_role = st.selectbox(
                "Роль",
                ["Backend-разработчик", "Frontend-разработчик", "QA-инженер", "Аналитик", "Team Lead", "DevOps", "Fullstack"],
                key="new_role"
            )
            new_grade = st.selectbox(
                "Грейд",
                ["Junior", "Middle", "Senior", "Lead"],
                key="new_grade"
            )
        
        with col2:
            new_skills = st.text_input("Навыки (через запятую)", placeholder="Python, SQL, Docker, React", key="new_emp_skills")
            new_available = st.number_input("Доступно часов", min_value=0, max_value=50, value=40, key="new_available")
            new_max = st.number_input("Максимум часов", min_value=0, max_value=50, value=40, key="new_max")
        
        if st.button("✅ Добавить сотрудника", key="add_employee_btn"):
            if new_name and new_skills:
                add_new_employee(
                    new_name,
                    new_role,
                    new_grade,
                    new_skills,
                    new_available,
                    new_max
                )
                st.success(f"✅ Сотрудник '{new_name}' успешно добавлен!")
                st.rerun()
            else:
                st.error("❌ Пожалуйста, заполните имя и навыки")
    
    # МАТРИЦА НАВЫКОВ (с цветовой подсветкой ячеек)
    st.subheader("📊 Матрица навыков сотрудников")
    st.caption("Таблица показывает, какими навыками владеет каждый сотрудник. 🟢 Зелёная ячейка — навык есть, ⚪ Прозрачная — навыка нет.")
    
    # Собираем все уникальные навыки
    all_skills = set()
    for skills in employees['skills']:
        all_skills.update(skills)
    all_skills = sorted(all_skills)
    
    # Создаём DataFrame: строки — сотрудники, столбцы — навыки
    skill_data = []
    for _, emp in employees.iterrows():
        emp_skills = set(emp['skills'])
        row = {'Сотрудник': emp['name']}
        for skill in all_skills:
            row[skill] = 1 if skill in emp_skills else 0
        skill_data.append(row)
    
    skill_df = pd.DataFrame(skill_data)
    skill_df = skill_df.set_index('Сотрудник')
    
    # Функция для подсветки ячеек
    def highlight_skills(val):
        if val == 1:
            return 'background-color: #90EE90'  # светло-зелёный
        else:
            return ''  # прозрачный
    
    # Применяем стиль к таблице
    styled_df = skill_df.style.map(highlight_skills)
    
    # Отображаем матрицу с подсветкой
    st.dataframe(
        styled_df,
        use_container_width=True
    )

# ========== РАЗДЕЛ: МОИ ЗАДАЧИ ==========
elif menu == "👤 Мои задачи":
    st.header("👤 Мои задачи")
    st.caption("Здесь вы можете посмотреть задачи, назначенные лично вам")
    
    # Выбор сотрудника
    employee_names = system.employees['name'].tolist()
    selected_employee = st.selectbox("Выберите сотрудника", employee_names, key="my_tasks_employee")
    
    if selected_employee:
        # Проверяем, есть ли уже выполненные распределения
        if st.session_state.get('distributed', False) and 'recommendations' in st.session_state:
            recommendations = st.session_state['recommendations']
            
            # Фильтруем задачи для выбранного сотрудника
            my_tasks = recommendations[recommendations['исполнитель'] == selected_employee]
            
            if len(my_tasks) > 0:
                st.subheader(f"📋 Задачи для {selected_employee}")
                
                # Показываем метрику
                total_hours = my_tasks['трудозатраты_ч'].sum()
                avg_compatibility = my_tasks['совместимость_%'].mean()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Количество задач", len(my_tasks))
                with col2:
                    st.metric("Всего трудозатрат (ч)", f"{total_hours:.0f}")
                with col3:
                    st.metric("Средняя совместимость", f"{avg_compatibility:.0f}%")
                
                # Таблица задач
                st.dataframe(
                    my_tasks[['задача', 'трудозатраты_ч', 'совместимость_%']],
                    use_container_width=True,
                    column_config={
                        "совместимость_%": st.column_config.ProgressColumn(
                            "Совместимость",
                            format="%.0f%%",
                            min_value=0,
                            max_value=100
                        )
                    }
                )
            else:
                st.info(f"📭 У {selected_employee} пока нет назначенных задач.")
        else:
            st.warning("⚠️ Распределение задач ещё не выполнено. Пожалуйста, обратитесь к тимлиду.")   

# ========== РАЗДЕЛ 4: ЗАДАЧИ ==========
elif menu == "📝 Задачи":
    st.header("📝 Список задач")
    
    # ПОИСК ПО НАЗВАНИЮ
    search_term = st.text_input("🔍 Поиск по названию задачи", placeholder="Введите слово для поиска...")
    
    # БАЗОВЫЙ ДАТАФРЕЙМ
    tasks_df = tasks[['id', 'title', 'required_skills', 'estimated_hours', 'priority', 'deadline']].copy()
    
    # ПРИМЕНЯЕМ ПОИСК
    if search_term:
        tasks_df = tasks_df[tasks_df['title'].str.contains(search_term, case=False, na=False)]
        st.caption(f"🔎 Найдено задач: {len(tasks_df)}")
    
    # ФИЛЬТРЫ
    st.subheader("🎯 Фильтры")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        priority_filter = st.multiselect(
            "Приоритет", 
            options=sorted(tasks['priority'].unique()), 
            default=sorted(tasks['priority'].unique())
        )
    
    with col2:
        min_hours = st.number_input(
            "Мин. трудозатраты (часы)", 
            min_value=0, 
            max_value=int(tasks['estimated_hours'].max()), 
            value=0
        )
    
    with col3:
        max_hours = st.number_input(
            "Макс. трудозатраты (часы)", 
            min_value=0, 
            max_value=int(tasks['estimated_hours'].max()), 
            value=int(tasks['estimated_hours'].max())
        )
    
    # ПРИМЕНЯЕМ ФИЛЬТРЫ
    tasks_df = tasks_df[tasks_df['priority'].isin(priority_filter)]
    tasks_df = tasks_df[tasks_df['estimated_hours'] >= min_hours]
    tasks_df = tasks_df[tasks_df['estimated_hours'] <= max_hours]
    
    # ОТОБРАЖАЕМ ТАБЛИЦУ
    st.dataframe(tasks_df, use_container_width=True)
    
    # УДАЛЕНИЕ ЗАДАЧ
    st.subheader("🗑️ Удаление задачи")
    col_del1, col_del2 = st.columns([3, 1])
    
    with col_del1:
        if len(tasks) > 0:
            task_to_delete = st.selectbox(
                "Выберите задачу для удаления", 
                tasks['title'].tolist(),
                key="delete_task_select"
            )
        else:
            st.info("Нет задач для удаления")
            task_to_delete = None
    
    with col_del2:
        st.write("")
        st.write("")
        if task_to_delete and st.button("❌ Удалить", type="secondary"):
            task_id = tasks[tasks['title'] == task_to_delete]['id'].iloc[0]
            delete_task(task_id)
            st.success(f"✅ Задача '{task_to_delete}' удалена!")
            st.rerun()
    
    # ДОБАВЛЕНИЕ НОВОЙ ЗАДАЧИ
    with st.expander("➕ Добавить новую задачу", expanded=False):
        st.subheader("➕ Новая задача")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_title = st.text_input("Название задачи", key="new_title")
            new_description = st.text_area("Описание", key="new_description")
            new_skills = st.text_input("Навыки (через запятую)", placeholder="Python, SQL, Docker", key="new_skills")
        
        with col2:
            new_hours = st.number_input("Трудозатраты (часы)", min_value=1, max_value=100, value=8, key="new_hours")
            new_priority = st.slider("Приоритет", min_value=1, max_value=5, value=3, key="new_priority")
            new_deadline = st.date_input("Дедлайн", key="new_deadline")
        
        if st.button("✅ Добавить задачу", key="add_task_btn"):
            if new_title and new_skills:
                add_new_task(
                    new_title,
                    new_description,
                    new_skills,
                    new_hours,
                    new_priority,
                    new_deadline.strftime("%Y-%m-%d")
                )
                st.success(f"✅ Задача '{new_title}' успешно добавлена!")
                st.rerun()
            else:
                st.error("❌ Пожалуйста, заполните название и навыки")

    # ДИАГРАММА ТРУДОЗАТРАТ
    st.subheader("⏱️ Трудозатраты по задачам")
    fig = px.bar(
        tasks,
        x='title',
        y='estimated_hours',
        color='priority',
        title="Оценка трудозатрат",
        labels={'title': 'Задача', 'estimated_hours': 'Часы', 'priority': 'Приоритет'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ========== РАЗДЕЛ 5: АНАЛИТИКА ==========
elif menu == "📈 Аналитика":
    st.header("📈 Аналитика эффективности")
    
    # Статистика по команде
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Средняя загрузка", f"{employees['available_hours'].mean():.0f} / {employees['max_hours'].mean():.0f} ч")
    with col2:
        all_skills_count = len(set([s for skills in employees['skills'] for s in skills]))
        st.metric("Всего навыков в команде", all_skills_count)
    with col3:
        st.metric("Средний приоритет задач", f"{tasks['priority'].mean():.1f}")
    
    # Распределение по ролям
    st.subheader("👥 Распределение по ролям")
    role_counts = employees['role'].value_counts()
    fig = px.pie(values=role_counts.values, names=role_counts.index, title="Состав команды")
    st.plotly_chart(fig, use_container_width=True)
    
    # Распределение по грейдам
    st.subheader("📊 Распределение по грейдам")
    grade_counts = employees['grade'].value_counts()
    fig2 = px.bar(x=grade_counts.index, y=grade_counts.values, title="Грейды сотрудников", labels={'x': 'Грейд', 'y': 'Количество'})
    st.plotly_chart(fig2, use_container_width=True)

# ========== РАЗДЕЛ 6: СРАВНЕНИЕ КРИТЕРИЕВ ==========
elif menu == "🔄 Сравнение критериев":
    st.header("🔄 Сравнение критериев оптимизации")
    
    st.markdown("""
    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:20px">
    <b>📖 Что здесь сравнивается?</b><br>
    • <b>Максимум компетенций</b> — назначает задачи тем, кто лучше всего подходит по навыкам<br>
    • <b>Сбалансированная загрузка</b> — учитывает также текущую занятость сотрудников
    </div>
    """, unsafe_allow_html=True)
    
    with st.spinner("🔄 Выполняется сравнение..."):
        rec_max, metrics_max, rec_balanced, metrics_balanced = compare_criteria(system)
    
    # Метрики сравнения
    st.subheader("📊 Сравнение метрик эффективности")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Средняя совместимость (Макс. компетенций)", f"{metrics_max['средняя_совместимость_%']}%")
        st.metric("Мин. совместимость (Макс. компетенций)", f"{metrics_max['минимальная_совместимость_%']}%")
        st.metric("Макс. совместимость (Макс. компетенций)", f"{metrics_max['максимальная_совместимость_%']}%")
    
    with col2:
        st.metric("Средняя совместимость (Сбалансированная)", f"{metrics_balanced['средняя_совместимость_%']}%")
        st.metric("Мин. совместимость (Сбалансированная)", f"{metrics_balanced['минимальная_совместимость_%']}%")
        st.metric("Макс. совместимость (Сбалансированная)", f"{metrics_balanced['максимальная_совместимость_%']}%")
    
    # Вывод преимуществ
    diff = metrics_max['средняя_совместимость_%'] - metrics_balanced['средняя_совместимость_%']
    
    if diff > 0:
        st.success(f"✅ **Максимум компетенций** даёт на {diff:.1f}% выше среднюю совместимость, но может перегружать сотрудников")
    elif diff < 0:
        st.success(f"✅ **Сбалансированная загрузка** лучше распределяет нагрузку, но средняя совместимость на {abs(diff):.1f}% ниже")
    else:
        st.info("⚖️ Оба критерия показывают одинаковые результаты")
    
    # Таблицы сравнения
    st.subheader("📋 Результаты распределения")
    
    tab1, tab2 = st.tabs(["🎯 Максимум компетенций", "⚖️ Сбалансированная загрузка"])
    
    with tab1:
        st.dataframe(rec_max, use_container_width=True)
    
    with tab2:
        st.dataframe(rec_balanced, use_container_width=True)

# ========== РАЗДЕЛ 7: ИСТОРИЯ ==========
elif menu == "📜 История":
    st.header("📜 История распределений")
    
    history = load_history()
    
    if not history:
        st.info("📭 История пока пуста. Выполните распределение задач, чтобы сохранить результаты.")
    else:
        st.caption(f"Всего сохранено распределений: {len(history)}")
        
        # Выбор записи для просмотра
        options = [f"{h['date']} — {h['criterion_name']}" for h in history]
        selected_idx = st.selectbox("Выберите распределение для просмотра", range(len(options)), format_func=lambda x: options[x])
        
        if selected_idx is not None:
            selected = history[selected_idx]
            
            st.subheader(f"📅 {selected['date']}")
            st.caption(f"Критерий: **{selected['criterion_name']}**")
            
            # Преобразуем в DataFrame
            df = pd.DataFrame(selected['assignments'])
            st.dataframe(df, use_container_width=True)
            
            # Кнопка экспорта истории в Excel
            if st.button("📥 Экспортировать историю в Excel", key="export_history_btn"):
                all_history_df = pd.DataFrame()
                for i, h in enumerate(history):
                    temp_df = pd.DataFrame(h['assignments'])
                    temp_df['дата_распределения'] = h['date']
                    temp_df['критерий'] = h['criterion_name']
                    all_history_df = pd.concat([all_history_df, temp_df], ignore_index=True)
                
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    all_history_df.to_excel(writer, sheet_name='История', index=False)
                
                st.download_button(
                    label="📥 Скачать всю историю Excel",
                    data=output.getvalue(),
                    file_name="история_распределений.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ========== РАЗДЕЛ 8: НАСТРОЙКИ ==========
elif menu == "⚙️ Настройки":
    st.header("⚙️ Настройки системы")
    st.info("Для изменения данных отредактируйте файлы:\n- `data/employees.json`\n- `data/tasks.json`")
    
    st.subheader("📖 О системе")
    st.markdown("""
    **Система интеллектуального распределения задач**  
    
    - Основана на **венгерском алгоритме** (решение задачи назначения)
    - Учитывает **компетенции** сотрудников (процент совпадения навыков)
    - Учитывает **текущую загрузку** (доступные часы)
    - Поддерживает два критерия оптимизации:
      - **Максимум компетенций** — назначает задачи тем, кто лучше всего подходит по навыкам
      - **Сбалансированная загрузка** — учитывает также текущую занятость сотрудников
    
    **Технологии:** Python, Streamlit, Pandas, NumPy, SciPy, Matplotlib, Plotly, Seaborn
    
    **Алгоритм:** Венгерский алгоритм (решение задачи о назначениях за O(n³))
    """)

st.sidebar.markdown("---")
st.sidebar.caption("Разработано в рамках ВКР | МАИ 2026")