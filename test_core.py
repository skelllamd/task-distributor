from core import TaskDistributorCore

system = TaskDistributorCore()
recommendations = system.run_full_pipeline(criterion='max_competency')

print("\n" + "=" * 50)
print("РЕКОМЕНДАЦИИ ПО РАСПРЕДЕЛЕНИЮ ЗАДАЧ")
print("=" * 50)
print(recommendations.to_string(index=False))

print("\n" + "=" * 50)
print("МЕТРИКИ ЭФФЕКТИВНОСТИ")
print("=" * 50)
metrics = system.calculate_metrics()
for key, value in metrics.items():
    print(f"{key}: {value}")