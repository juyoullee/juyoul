def filter_shadow(actions, use_shop):
    filtered = {}

    for name, action in actions.items():
        idx = int(name.split(".")[0].split("_")[0])

        if 7 <= idx <= 10:
            if use_shop:
                filtered[name] = action
        else:
            filtered[name] = action

    return filtered
