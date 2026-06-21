# export_twitter.py — Export Twitter-mode simulation traces from SQLite to Neo4j.
# Reads the trace table and creates User nodes + FOLLOWS relationships in Neo4j.
# Handles integer timesteps (Twitter mode) where created_at is a step counter.

from __future__ import annotations

import json
import os
import sqlite3

from neo4j import GraphDatabase


def connect_neo4j(uri: str | None = None, username: str | None = None, password: str | None = None):
    uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = username or os.getenv("NEO4J_USERNAME", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(username, password))


def _create_user_node(tx, user_id: int, info: dict, created_at):
    query = (
        "MERGE (u:User {user_id: $user_id}) "
        "SET u += $info, u.created_at = $created_at"
    )
    tx.run(query, user_id=user_id, info=info, created_at=created_at)


def _create_follow_edge(tx, follower_id: int, followee_id: int, timestamp):
    query = (
        "MERGE (u1:User {user_id: $follower_id}) "
        "MERGE (u2:User {user_id: $followee_id}) "
        "CREATE (u1)-[:FOLLOWS {timestamp: $timestamp}]->(u2)"
    )
    tx.run(query, follower_id=follower_id, followee_id=followee_id, timestamp=timestamp)


def export_twitter_to_neo4j(
    db_path: str,
    neo4j_uri: str | None = None,
    neo4j_username: str | None = None,
    neo4j_password: str | None = None,
):
    driver = connect_neo4j(neo4j_uri, neo4j_username, neo4j_password)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with driver.session() as session:
        cursor.execute("SELECT user_id, user_name, name, bio, created_at FROM user ORDER BY created_at")
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


def export_traces_to_neo4j(
    db_path: str,
    neo4j_uri: str | None = None,
    neo4j_username: str | None = None,
    neo4j_password: str | None = None,
):
    driver = connect_neo4j(neo4j_uri, neo4j_username, neo4j_password)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with driver.session() as session:
        cursor.execute("SELECT user_id, created_at, action, info FROM trace ORDER BY created_at")
        for row in cursor:
            user_id, created_at, action, info_str = row
            info = json.loads(info_str) if info_str else {}

            if action == "sign_up":
                session.execute_write(_create_user_node, user_id, info, created_at)
            elif action == "follow":
                params = info.get("params", {})
                follow_target = params.get("user_id") or info.get("follow_id")
                if follow_target:
                    session.execute_write(_create_follow_edge, user_id, int(follow_target), created_at)

    conn.close()
    driver.close()


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "simulation.db"
    print(f"Exporting {db_path} to Neo4j...")
    export_twitter_to_neo4j(db_path)
    print("Done.")
