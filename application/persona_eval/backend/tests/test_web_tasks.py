from backend.service.web_tasks import get_web_eval_task, list_web_eval_tasks


def test_web_task_path_is_absolute_and_catalog_resolves():
    """task_path must resolve from any CWD so the real site catalog loads.

    The demo runs uvicorn from the persona_eval dir, so a relative task_path
    silently misses the catalog and the trace falls back to placeholder products.
    """
    task = get_web_eval_task("web-ecommerce-platform_product-discovery")
    assert task.task_path.is_absolute()
    catalog = task.task_path / "environment" / "ecommerce-web" / "site" / "catalog.json"
    assert catalog.is_file(), "real catalog.json not found at {}".format(catalog)


def test_all_registered_web_tasks_have_absolute_paths():
    for task in list_web_eval_tasks():
        assert task.task_path.is_absolute(), "{} has relative task_path".format(task.id)
