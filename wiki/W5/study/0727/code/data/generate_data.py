import argparse
import csv
import random

COUNTRIES = ["KR", "US", "JP", "DE", "FR"]


def generate_users(path, n_users, seed, skew):
    random.seed(seed)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "name", "country"])
        for user_id in range(1, n_users + 1):
            if skew and random.random() < 0.8:
                country = COUNTRIES[0]
            else:
                country = random.choice(COUNTRIES)
            writer.writerow([user_id, f"user_{user_id}", country])


def generate_orders(path, n_orders, n_users, seed):
    random.seed(seed + 1)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "user_id", "amount"])
        for order_id in range(1, n_orders + 1):
            user_id = random.randint(1, n_users)
            amount = round(random.uniform(1.0, 500.0), 2)
            writer.writerow([order_id, user_id, amount])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=5000)
    parser.add_argument("--orders", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skew", action="store_true")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    users_path = f"{args.out_dir}/users.csv"
    orders_path = f"{args.out_dir}/orders.csv"

    generate_users(users_path, args.users, args.seed, args.skew)
    generate_orders(orders_path, args.orders, args.users, args.seed)

    print(f"wrote {args.users} users to {users_path}")
    print(f"wrote {args.orders} orders to {orders_path}")


if __name__ == "__main__":
    main()
