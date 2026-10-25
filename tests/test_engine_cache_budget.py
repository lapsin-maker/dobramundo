from dobramundo.engine.cache import BoundedCache, CacheBudget


def test_global_budget_counts_subsurface_backing_once_and_forgets_on_clear(display):
    budget = CacheBudget(1024 * 1024)
    first = BoundedCache(4, budget=budget)
    second = BoundedCache(4, budget=budget)
    source = display.subsurface((0, 0, 48, 32)).copy()
    view = source.subsurface((2, 2, 16, 12))

    first["source"] = source
    retained = source.get_pitch() * source.get_height()
    second["view"] = view
    assert budget.retained_bytes() == retained

    del first["source"]
    assert budget.retained_bytes() == retained
    second.clear()
    assert budget.retained_bytes() == 0


def test_global_budget_trims_oldest_entry_across_cache_owners(display):
    one = display.subsurface((0, 0, 4, 4)).copy()
    two = display.subsurface((4, 0, 4, 4)).copy()
    budget = CacheBudget(one.get_pitch() * one.get_height())
    older = BoundedCache(8, budget=budget)
    newer = BoundedCache(8, budget=budget)

    older["old"] = one
    newer["new"] = two

    assert "old" not in older
    assert newer.get("new") is two
    assert budget.retained_bytes() == two.get_pitch() * two.get_height()
