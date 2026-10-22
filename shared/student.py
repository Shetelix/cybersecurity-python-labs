"""Персональні дані студента, спільні для всіх лабораторних робіт."""

STUDENT_NAME = "Шетеля Дмитро Максимович"
GROUP_NAME = "КБ-209"
VARIANT_NUMBER = 23

# У методичці 15 варіантів вхідних даних, тому для номера варіанта
# понад 15 дані беруться циклічно: 23 -> 8.
DATA_VARIANTS_COUNT = 15
DATA_VARIANT = (VARIANT_NUMBER - 1) % DATA_VARIANTS_COUNT + 1
