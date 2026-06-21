# export_reddit.py — Export Reddit-mode simulation traces from SQLite to Neo4j.
# Reads user + follow tables and creates nodes + FOLLOWS relationships.
# Handles datetime timestamps (Reddit mode uses time_transfer with magnification).

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime

from neo4j import GraphDatabase


def connect_neo4j(uri: str | None = None, username: str | None = None, password: str | None = None):
    uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = username or os.getenv("NEO4J_USERNAME", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(username, password))


def _format_datetime(dt_string: str) -> str:
    try:
        dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S.%f")
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"
        except (ValueError, TypeError):
            return str(dt_string)


def _create_user_node(tx, user_id: int, info: dict, created_at: str):
    formatted = _format_datetime(created_at)
    query = (
        "MERGE (u:User {user_id: $user_id}) "
        "SET u += $info, u.created_at = datetime($created_at)"
    )
    tx.run(query, user_id=user_id, info=info, created_at=formatted)


def _create_follow_edge(tx, follower_id: int, followee_id: int, created_at: str):
    formatted = _format_datetime(created_at)
    query = (
        "MERGE (u1:User {user_id: $follower_id}) "
        "MERGE (u2:User {user_id: $followee_id}) "
        "CREATE (u1)-[:FOLLOWS {created_at: datetime($created_at)}]->(u2)"
    )
    tx.run(query, follower_id=follower_id, followee_id=followee_id, created_at=formatted)


def export_reddit_to_neo4j(
    db_path: str,
    neo4j_uri: str | None = None,
    neo4j_username: str | None = None,
    neo4j_password: str | None = None,
):
    driver = connect_neo4j(neo4j_uri, neo4j_username, neo4j_password)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with driver.session() as session:
        cursor.execute("SELECT user_id, user_name, name, bio, created_at FROM user ORDER BY user_id")
        for row in cursor:
            user_id, user_name, name, bio, created_at = row
            info = {"user_name": user_name, "name": name, "bio": bio or ""}
            session.execute_write(_create_user_node, user_id, info, created_at)

        cursor.execute("SELECT follower_id, followee_id, created_at FROM follow ORDER BY created_at")
        for row in cursor:
            follower_id, followee_id, created_at = row
            session.execute_write(_create_follow_edge, follower_id, followee_id, created_at)

    conn.close()
    driver.close()


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "simulation.db"
    print(f"Exporting {db_path} to Neo4j (Reddit mode)...")
    export_reddit_to_neo4j(db_path)
    print("Done.")
