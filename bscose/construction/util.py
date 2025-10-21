

class DisplayFormatter:
    def __init__(self):
        self.lines_and_parts: list[list[str]] = []


    def add_parts(self, *parts: str) -> None:
        self.lines_and_parts.append(list(parts))

    def get_parts_formatted(self) -> list[str]:
        max_num_parts_in_line = -1
        adjusted_lines: list[list[str]] = []
        for line in self.lines_and_parts:
            adjusted_lines.append([])
            if len(line) > max_num_parts_in_line:
                max_num_parts_in_line = len(line)

        for i in range(max_num_parts_in_line):
            # now, for each line, if they have a part at the index, get it's max str-length
            max_part_length = -1
            for j in range(len(self.lines_and_parts)):
                line = self.lines_and_parts[j]
                if i >= len(line): # if the index is out-of bounds
                    continue
                if len(line[i]) > max_part_length:
                    max_part_length = len(line[i])

            for j in range(len(self.lines_and_parts)):
                line = self.lines_and_parts[j]
                if i >= len(line): # if the index is out-of bounds
                    continue
                adjusted_line = f"{line[i]}{' ' * (max_part_length - len(line[i]))}"
                adjusted_lines[j].append(adjusted_line)
        result = [("".join(line).strip()) for line in adjusted_lines]
        return result


