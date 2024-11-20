class Registry:
    def __init__(self, name):
        """Map strings to classes.

        Registered object can be built from registry.

        Args:
            name (str): Registry name.
        """
        self._name = name
        self._module_dict = dict()

    def __len__(self):
        return len(self._module_dict)

    def __contains__(self, key):
        return self.get(key) is not None

    def __repr__(self):
        format_str = self.__class__.__name__ + \
                     f'(name={self._name}, ' \
                     f'items={self._module_dict})'
        return format_str

    @property
    def name(self):
        return self._name

    @property
    def module_dict(self):
        return self._module_dict

    def get(self, key):
        """Get the registry record.

        Args:
            key (str): The class name in string format.

        Returns:
            class: The corresponding class.
        """
        return self._module_dict[key]

    def _register_module(self, module_class, module_name=None):
        if module_name is None:
            module_name = module_class.__name__
        elif isinstance(module_name, str):
            module_name = [module_name]
        else:
            msg = f'Module name should be str type. But given: {type(module_name)}'
            raise TypeError(msg)

        if module_name in self._module_dict:
            raise KeyError(f'{module_name} is already registered in {self.name}')
        self._module_dict[module_name] = module_class

    def register_module(self, module_name=None):
        """Register a module.

        A record will be added to `self._module_dict` whose key is the class name or the specified name,
        and value is the class itself. It can be used as a decorator.
        E.g., @x.register_module()

        Args:
            module_name (str): The module name to be registered. If not specified, the class name will be used.
        """
        def _register(cls):
            self._register_module(module_class=cls, module_name=module_name)
            return cls

        return _register


Norm = Registry('Norm')