const { Pool } = require('pg');

const pool = new Pool({
    host: '72.60.89.5',
    port: 5433,
    user: 'postgres',
    password: 'bigmoneycoming',
    database: 'bd_vet_empatia3'
    // SSL removido explicitamente pois o servidor não suporta
});

async function testConnection() {
    try {
        console.log('Testing connection to PostgreSQL...');
        console.log(`Host: ${pool.options.host}:${pool.options.port}`);
        console.log(`User: ${pool.options.user}`);

        const client = await pool.connect();
        console.log('✅ Connected successfully!');

        const res = await client.query('SELECT version()');
        console.log('PostgreSQL version:', res.rows[0].version);

        client.release();
        await pool.end();
    } catch (err) {
        console.error('❌ Connection failed:', err.message);
        if (err.message.includes('password')) {
            console.error('Hint: Double check the password provided.');
        } else if (err.message.includes('SSL')) {
            console.error('Hint: SSL issue detected.');
        }
        process.exit(1);
    }
}

testConnection();
