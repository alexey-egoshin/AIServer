class Ai:
    id = None
    __location = None
    __country = None

    def __init__(self):
        pass

    def get_commands(self, game):
        return [{"commandName": "moveOrAttack", "arguments": {"arg1": "value1"}}]

    def generate_position(self, type_unit, troop_size, i, amount):
        country_bound = self.__location["boundsCountry"][self.__country]
        return [
            (country_bound["NE"][0] + country_bound["SW"][0]) / 2,
            (country_bound["NE"][1] + country_bound["SW"][1]) / 2,
        ]

    def generate_unit_positions(self, unit_counts):
        unit_positions = []
        for type_unit in unit_counts:
            for troop_size in unit_counts[type_unit]:
                amount = unit_counts[type_unit][troop_size]
                for i in range(amount):
                    unit_positions.append({
                        "country": self.__country,
                        "type": type_unit,
                        "position": self.generate_position(type_unit, troop_size, i, amount),
                        "troopSize": troop_size,
                    })
        return unit_positions

    def get_location(self):
        return self.__location

    def set_location(self, location):
        self.__location = location

    def get_country(self):
        return self.__country

    def set_country(self, country):
        self.__country = country
