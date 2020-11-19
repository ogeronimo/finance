import os
import re
# Python 3.x code
# Imports
import tkinter
from tkinter import messagebox

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# HOME/INDEX-------------------------
@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Query database for user's stocks
    stocks = db.execute("SELECT symbol, shares FROM transactions WHERE user_id = :user_id ORDER BY symbol DESC",
                    user_id = session["user_id"])

    # Ensure user has stocks
    if not stocks:
        return render_template("index.html", cash=usd(10000),message = "Portfolio is empty.")

    rows= db.execute("SELECT symbol, SUM(shares) as totalShares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING totalShares > 0;",
            user_id=session["user_id"])
    allData = []
    allTotal = 0
    for row in rows:
        stock = lookup(row["symbol"])
        allData.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "shares": row["totalShares"],
            "price": usd(stock["price"]),
            "total": usd(stock["price"] * row["totalShares"])
        })
        allTotal += stock["price"] * row["totalShares"]
    rows= db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    cash = rows[0]["cash"]
    allTotal += cash

    # Redirect user to index
    return render_template("index.html", allData=allData, cash=usd(cash), allTotal=usd(allTotal))

# Buy-----------------------------------------
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        # Ensure share was submitted
        if not request.form.get("shares"):
            return apology("missing shares", 400)

        # Ensure positive integer of share was submitted
        if not request.form.get("shares").isdigit():
            return apology("invalid number of shares", 400)

        # Insert symbol and shares to lookup using form
        shares = int(request.form.get("shares"))
        symbol = request.form.get("symbol").upper()
        stock = lookup(symbol)

        # Ensure stock is valid
        if stock == None:
            return apology("invalid symbol", 400)

        ##Select  Cash from user by querying database
        rows = db.execute("SELECT cash FROM users WHERE id=:id",
                            id=session["user_id"])
        moneyBlance = rows[0]['cash']
        ##Calcs for total amount purchased
        NewBalance = moneyBlance - shares * stock['price']

        #Ensure purchase is valid
        if NewBalance < 0:
            return apology("Can't afford", 400)

        # Insert (NewBalance) to user's profile
        db.execute("UPDATE users SET cash=:NewBalance WHERE id=:id",
                    NewBalance=NewBalance, id=session["user_id"])

        # Query database to insert transaction
        db.execute("INSERT INTO transactions (user_id, type, symbol, shares, price) VALUES (:user_id, :transaction_type, :symbol, :shares, :price)",
                    user_id = session["user_id"],
                    transaction_type = "purchase",
                    symbol = stock["symbol"],
                    shares = int(shares),
                    price = stock["price"])
        flash("Bought!")
        # Redirect user to home page
        return redirect("/")
        # return render_template("index.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    rows= db.execute("SELECT * FROM transactions WHERE user_id = :user_id", user_id=session["user_id"])
    allData = []
    for row in rows:
        stock = lookup(row["symbol"])
        allData.append({
            "symbol": stock["symbol"],
            "shares": row["shares"],
            "price": usd(stock["price"]),
            "date": row["date"],
            "type": row["type"]
        })

    # Redirect user to index
    return render_template("history.html", allData=allData)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# QUOTE-----------------------------------------
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure quote was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        # Insert Quote lookup using form
        symbol = request.form.get("symbol").upper()
        stock = lookup(symbol)

        # Ensure quote is valid
        if stock == None:
            return apology("invalid symbol", 400)

        # return quote price
        else:
            return render_template("quoted.html", validStock = stock)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

# REGISTER------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password and password (again) matched
        if request.form.get("password") != request.form.get("password2"):
            return apology("password don't match", 400)

        # #Require users’ passwords to have some number of letters, numbers, and/or symbols.
        # while True:
        #     password = request.form.get("password")
        #     if len(password) < 8:
        #         return apology("Make sure your password is at lest 8 letters", 400)
        #     elif re.search('[0-9]',password) is None:
        #         return apology("Make sure your password has a number in it", 400)
        #     elif re.search('[A-Z]',password) is None:
        #         return apology("Make sure your password has a capital letter in it", 400)
        #     else:
        #         break

       # Insert Query to database (username and password)
        rows = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                      username=request.form.get("username"),
                      hash=generate_password_hash(request.form.get("password")))

        # Ensure username is available
        if rows is None:
            return apology("Username NOT available", 403)

        # Remember which user has logged in
        session["user_id"] = rows

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        # Ensure share was submitted
        if not request.form.get("shares"):
            return apology("missing shares", 400)

        # Ensure positive integer of share was submitted
        if not request.form.get("shares").isdigit():
            return apology("invalid number of shares", 400)

        # Insert symbol and shares to lookup using form
        shares = int(request.form.get("shares"))
        symbol = request.form.get("symbol").upper()
        stock = lookup(symbol)
        # Ensure stock is valid
        if stock == None:
            return apology("invalid symbol", 400)

        # Check user's stock amount to sell
        rows = db.execute("SELECT symbol, SUM(shares) as totalShares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING totalShares > 0;",
                user_id=session["user_id"])
        for row in rows:
            if row["symbol"] == symbol:
                if shares > row["totalShares"]:
                    return apology("Can't sell, too many shares", 400)

        ##Select  Cash from user by querying database
        rows = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        moneyBlance = rows[0]['cash']
        ##Calcs for total amount purchased
        NewBalance = moneyBlance + shares * stock['price']

        # Insert (NewBalance) to user's profile
        db.execute("UPDATE users SET cash=:NewBalance WHERE id=:id",
                    NewBalance=NewBalance, id=session["user_id"])

        # Query database to insert transaction
        db.execute("INSERT INTO transactions (user_id, type, symbol, shares, price) VALUES (:user_id, :transaction_type, :symbol, :shares, :price)",
                    user_id = session["user_id"],
                    transaction_type = "sold",
                    symbol = stock["symbol"],
                    shares = -1 * shares,
                    price = stock["price"])
        flash("Sold!")
        # Redirect user to home page
        return redirect("/")
        # return render_template("index.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        #Display symbols available per user
        rows = db.execute("SELECT symbol FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING SUM(shares) > 0;",user_id=session["user_id"])
        userSymbol= []
        for row in rows:
            stock = lookup(row["symbol"])
            userSymbol.append({"symbol":stock["symbol"]})

        return render_template("sell.html", userSymbol=userSymbol)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

