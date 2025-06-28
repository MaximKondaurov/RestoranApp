# Restaurant Management System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.4+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

A comprehensive restaurant management system built with Python and PySide6 for efficient table reservations, order management, and billing.

## Features

- **User Authentication**
  - Login/Register system
  - Admin and regular user roles

- **Table Management**
  - Add/Edit/Delete tables
  - Table availability status
  - Capacity management

- **Reservation System**
  - Book tables by date and time
  - Customer information storage
  - Reservation status tracking

- **Order Management**
  - Create and track orders
  - Order status updates
  - Menu item selection

- **Menu Management**
  - Add/Edit/Delete menu items
  - Price and ingredient tracking
  - Category organization

- **Billing System**
  - Generate receipts
  - Track payments
  - Create combined bills

- **Statistics**
  - Waiter performance metrics
  - Sales reporting

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/restaurant-management-system.git
   cd restaurant-management-system
   ```

2. Install dependencies:
   ```bash
   pip install PySide6
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. **Login Screen**
   - Use the login form to access the system
   - Admin credentials have full access
   - Regular users have limited functionality

2. **Main Interface**
   - Navigate between tabs using the top menu
   - Manage tables, reservations, orders, and receipts

3. **Data Management**
   - All data is stored in text files in the `restaurant_data` directory
   - No database setup required

## Screenshots

![Login Screen](screenshots/login.png)
*Login Screen*

![Main Interface](screenshots/main.png)
*Main Application Interface*

## File Structure

```
restaurant-management-system/
├── main.py                # Main application file
├── restaurant_data/       # Data storage directory
│   ├── customers.txt      # Customer database
│   ├── menuItems.txt      # Menu items database
│   ├── orders.txt         # Orders database
│   ├── receipts.txt       # Receipts database
│   ├── reservations.txt   # Reservations database
│   ├── restaurantTables.txt # Tables database
│   └── waiters.txt        # User accounts database
└── README.md              # This file
```

## Requirements

- Python 3.8+
- PySide6

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements.

## Support

For support or questions, please open an issue in the repository.
