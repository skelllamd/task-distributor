"""
Ядро системы интеллектуального распределения задач
"""

import json
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment


class TaskDistributorCore:
    """Класс для распределения задач"""
    
    def __init__(self):
        self.employees = None
        self.tasks = None
        self.competency_matrix = None
        self.assignment = None
        
    def load_employees(self, filepath='data/employees.json'):
        """Загрузка сотрудников из JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.employees = pd.DataFrame(data['employees'])
        print(f"Загружено сотрудников: {len(self.employees)}")
        return self.employees
    
    def load_tasks(self, filepath='data/tasks.json'):
        """Загрузка задач из JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.tasks = pd.DataFrame(data['tasks'])
        print(f"Загружено задач: {len(self.tasks)}")
        return self.tasks
    
    def build_competency_matrix(self):
        """Построение матрицы компетенций (задачи × сотрудники)"""
        n_tasks = len(self.tasks)
        n_employees = len(self.employees)
        matrix = np.zeros((n_tasks, n_employees))
        
        for i, task in self.tasks.iterrows():
            required_skills = set(task['required_skills'])
            
            for j, emp in self.employees.iterrows():
                employee_skills = set(emp['skills'])
                
                if len(required_skills) == 0:
                    matrix[i, j] = 1.0
                else:
                    match_count = len(required_skills.intersection(employee_skills))
                    matrix[i, j] = match_count / len(required_skills)
        
        self.competency_matrix = matrix
        print(f"Построена матрица компетенций: {matrix.shape[0]} задач × {matrix.shape[1]} сотрудников")
        return matrix
    
    def optimize(self, criterion='max_competency'):
        """Оптимизация распределения задач"""
        n_tasks = len(self.tasks)
        n_employees = len(self.employees)
        
        # Стоимость = обратная компетенция
        cost_matrix = 1 - self.competency_matrix
        
        # Если критерий сбалансированный — добавляем штраф за перегрузку
        if criterion == 'balanced':
            available = self.employees['available_hours'].values
            max_available = self.employees['max_hours'].values
            load_penalty = (max_available - available) / max_available
            for j in range(n_employees):
                cost_matrix[:, j] += load_penalty[j] * 0.5
        
        # Если задач больше, чем сотрудников — дополняем фиктивными
        if n_tasks > n_employees:
            cost_matrix = np.pad(
                cost_matrix, 
                ((0, 0), (0, n_tasks - n_employees)),
                constant_values=1e6
            )
        
        # Венгерский алгоритм
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # Сохраняем только реальные назначения
        self.assignment = []
        for task_idx, emp_idx in zip(row_ind, col_ind):
            if emp_idx < n_employees:
                self.assignment.append({
                    'task_idx': task_idx,
                    'emp_idx': emp_idx,
                    'task_id': self.tasks.iloc[task_idx]['id'],
                    'task_title': self.tasks.iloc[task_idx]['title'],
                    'employee_name': self.employees.iloc[emp_idx]['name'],
                    'competency_score': self.competency_matrix[task_idx, emp_idx]
                })
        
        print(f"Распределено задач: {len(self.assignment)}")
        return self.assignment
    
    def get_recommendations(self):
        """Получение рекомендаций в виде DataFrame"""
        if self.assignment is None:
            return None
        
        recommendations = []
        for a in self.assignment:
            rec = {
                'id_задачи': a['task_id'],
                'задача': a['task_title'],
                'исполнитель': a['employee_name'],
                'совместимость_%': round(a['competency_score'] * 100, 1),
                'трудозатраты_ч': self.tasks.iloc[a['task_idx']]['estimated_hours'],
                'доступно_часов': self.employees.iloc[a['emp_idx']]['available_hours']
            }
            recommendations.append(rec)
        
        return pd.DataFrame(recommendations)
    
    def calculate_metrics(self):
        """Расчёт метрик эффективности"""
        if self.assignment is None:
            return None
        
        metrics = {
            'общее_количество_задач': len(self.assignment),
            'средняя_совместимость_%': round(np.mean([a['competency_score'] for a in self.assignment]) * 100, 1),
            'минимальная_совместимость_%': round(np.min([a['competency_score'] for a in self.assignment]) * 100, 1),
            'максимальная_совместимость_%': round(np.max([a['competency_score'] for a in self.assignment]) * 100, 1),
            'количество_сотрудников': len(self.employees),
            'всего_задач_в_системе': len(self.tasks)
        }
        return metrics
    
    def run_full_pipeline(self, criterion='max_competency'):
        """Запуск полного пайплайна"""
        print("=" * 50)
        print("Запуск системы интеллектуального распределения задач")
        print("=" * 50)
        
        self.load_employees()
        self.load_tasks()
        self.build_competency_matrix()
        self.optimize(criterion=criterion)
        
        return self.get_recommendations()