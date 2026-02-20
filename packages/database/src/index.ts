import { drizzle, type NodePgDatabase } from "drizzle-orm/node-postgres";
import { Pool } from "pg";


export interface DatabaseConfig {
  connectionString: string;
  max?: number;
  idleTimeoutMillis?: number;
}

export type DataBase = NodePgDatabase;


export function createDatabase(config: DatabaseConfig) {
  const pool = new Pool({
    connectionString: config.connectionString,
    max: config.max ?? 5,
    idleTimeoutMillis: config.idleTimeoutMillis ?? 30000
  });
  
  return drizzle({ client: pool, casing: "snake_case" });
}