class draw_dynamic_table:
    def __init__(self):
        """Dynamically generates and draws the character mapping table."""
        print("Decimal | MSB | Second MSB | Third MSB | LSB | Character | Hex")
        print("-------- | --- | ----------- | --------- | --- | --------- | ---")
        
        for decimal in range(16):
            binary_repr = f"{decimal:04b}"  # Get the binary representation (4 bits)
            msb, second_msb, third_msb, lsb = binary_repr
            # Use ASCII characters for the corresponding decimal values
            if decimal < 10:
                character = chr(decimal + 48)  # '0' to '9'
            elif decimal == 10:
                character = '!'  # ASCII 33
            elif decimal == 11:
                character = '-'  # ASCII 45
            elif decimal == 12:
                character = '.'  # ASCII 46
            elif decimal == 13:
                character = ')'  # ASCII 41
            elif decimal == 14:
                character = '&'  # ASCII 38
            elif decimal == 15:
                character = '/'  # ASCII 47
            
            hex_repr = f"{decimal:02X}"  # Get the hexadecimal representation (2 digits)
            print(f"{decimal:8d} | {msb}   | {second_msb}         | {third_msb}     | {lsb}  | {character:9} | {hex_repr}")

    def draw_table(self):
        """Draws the literal/character mapping table to the console."""
        # Define the characters for each cell
        table = [
            ['Decimal', 'Hex', 'MSB', 'Second MSB', 'Third MSB', 'LSB', 'Uppercase', 'Lowercase'],
            ['0', '00', '0', '0', '0', '0', '0', '0'],
            ['1', '01', '0', '0', '0', '1', '1', '1'],
            ['2', '02', '0', '0', '1', '0', '2', '2'],
            ['3', '03', '0', '0', '1', '1', '3', '3'],
            ['4', '04', '0', '1', '0', '0', '4', '4'],
            ['5', '05', '0', '1', '0', '1', '5', '5'],
            ['6', '06', '0', '1', '1', '0', '6', '6'],
            ['7', '07', '0', '1', '1', '1', '7', '7'],
            ['8', '08', '1', '0', '0', '0', '8', '8'],
            ['9', '09', '1', '0', '0', '1', '9', '9'],
            ['10', '0A', '1', '0', '1', '0', '!', '!'],
            ['11', '0B', '1', '0', '1', '1', '-', '-'],
            ['12', '0C', '1', '1', '0', '0', '.', '.'],
            ['13', '0D', '1', '1', '0', '1', ')', ')'],
            ['14', '0E', '1', '1', '1', '0', '&', '&'],
            ['15', '0F', '1', '1', '1', '1', '/', '/']
        ]

        # Calculate the maximum width of each column for formatting
        column_widths = [max(len(str(cell)) for cell in column) for column in zip(*table)]

        # Print the table
        for row in table:
            for i, cell in enumerate(row):
                print(f"{cell:<{column_widths[i]}}", end=" ")
            print()

if __name__ == "__main__":
    dt = draw_dynamic_table()  # Create an instance
    dt.draw_table()  # Call the draw_table method on the instance
