import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN STREAMLIT ---
st.set_page_config(
    page_title="Aplikasi Manajemen Stok & Keuangan Toko",
    page_icon="📦",
    layout="wide"
)

# --- INISIALISASI DATABASE & AKUN DEFAULT ---
def init_db():
    conn = sqlite3.connect("stok_toko.db")
    cursor = conn.cursor()
    
    # Tabel Master Barang
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang (
            sku TEXT PRIMARY KEY,
            nama_barang TEXT NOT NULL,
            kategori TEXT,
            harga_beli REAL,
            harga_jual REAL,
            stok_min INTEGER
        )
    """)
    
    # Tabel Transaksi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            jenis TEXT,
            sku TEXT,
            jumlah INTEGER,
            harga_satuan REAL,
            total_harga REAL,
            keterangan TEXT,
            FOREIGN KEY(sku) REFERENCES barang(sku) ON DELETE CASCADE
        )
    """)

    # Tabel Pengguna (Login Role)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Masukkan Akun Default jika belum ada
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users VALUES ('admin', 'admin123', 'admin')")
        cursor.execute("INSERT INTO users VALUES ('kasir', 'kasir123', 'user')")
        conn.commit()

    conn.close()

# Fungsi helper untuk menghitung stok terkini suatu SKU
def get_stok_terkini(sku):
    conn = sqlite3.connect("stok_toko.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(jumlah) FROM transaksi WHERE sku=? AND jenis='MASUK'", (sku,))
    masuk = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(jumlah) FROM transaksi WHERE sku=? AND jenis='KELUAR'", (sku,))
    keluar = cursor.fetchone()[0] or 0
    conn.close()
    return masuk - keluar

# Jalankan inisialisasi database
init_db()

# --- MANAJEMEN SESI LOGIN DI STREAMLIT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# ================= HALAMAN LOGIN =================
if not st.session_state.logged_in:
    st.title("🔑 Login Sistem Toko")
    st.write("Silakan masukkan akun Anda untuk masuk ke aplikasi.")
    
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Masuk", use_container_width=True)
        
        if submit_btn:
            conn = sqlite3.connect("stok_toko.db")
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username_input, password_input))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = row[0]
                st.success(f"Login Berhasil sebagai [{row[0].upper()}]!")
                st.rerun()
            else:
                st.error("Username atau Password salah!")
                
   # st.info("💡 **Info Akun Bawaan:**\n- Admin: `admin` / `admin123`\n- Kasir: `kasir` / `kasir123`")
    st.stop()

# ================= HALAMAN UTAMA (SETELAH LOGIN) =================
# Header Top Bar & Tombol Logout
col_top1, col_top2 = st.columns([4, 1])
with col_top1:
    st.markdown(f"👤 **Pengguna:** `{st.session_state.username.upper()}` | **Role:** `[{st.session_state.role.upper()}]`")
with col_top2:
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()

st.markdown("---")
st.title("📦 Aplikasi Manajemen Stok & Keuangan Toko")

# --- PENGATURAN MENU BERDASARKAN ROLE ---
if st.session_state.role == "admin":
    menu_options = [
        "Cek Stok & Keuangan", 
        "Master Barang", 
        "Input Transaksi", 
        "Riwayat Barang Masuk", 
        "Riwayat Barang Keluar", 
        "Laporan Barang Terlaris"
    ]
else:
    # Kasir / User biasa dibatasi hanya melihat laporan & riwayat
    menu_options = [
        "Cek Stok & Keuangan", 
        "Riwayat Barang Masuk", 
        "Riwayat Barang Keluar"
    ]

selected_menu = st.sidebar.selectbox("📂 Pilih Menu", menu_options)


# ================= MENU 1: CEK STOK & KEUANGAN =================
if selected_menu == "Cek Stok & Keuangan":
    st.subheader("📊 Ringkasan Stok Produk & Keuangan Toko")
    
    conn = sqlite3.connect("stok_toko.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total_harga) FROM transaksi WHERE jenis='KELUAR'")
    total_masuk_uang = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(total_harga) FROM transaksi WHERE jenis='MASUK'")
    total_keluar_uang = cursor.fetchone()[0] or 0
    conn.close()

    m1, m2 = st.columns(2)
    m1.metric("Total Pemasukan (Penjualan)", f"Rp {total_masuk_uang:,.0f}")
    m2.metric("Total Pengeluaran (Restock)", f"Rp {total_keluar_uang:,.0f}")
    
    st.markdown("---")
    
    # Ambil data barang & stok terkini
    conn = sqlite3.connect("stok_toko.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sku, nama_barang, kategori, harga_beli, harga_jual, stok_min FROM barang")
    rows = cursor.fetchall()
    conn.close()
    
    data_tabel = []
    for row in rows:
        sku, nama, kat, h_beli, h_jual, stok_min = row
        stok_aktif = get_stok_terkini(sku)
        status = "⚠️ PERLU RESTOCK" if stok_aktif <= stok_min else "Aman"
        data_tabel.append({
            "SKU": sku, "Nama Barang": nama, "Kategori": kat, 
            "H. Beli": h_beli, "H. Jual": h_jual, 
            "Stok Min": stok_min, "Stok Aktif": stok_aktif, "Status": status
        })
        
    df_barang = pd.DataFrame(data_tabel)
    if not df_barang.empty:
        st.dataframe(df_barang, use_container_width=True)
        
        # Download Excel Ringkasan Stok
        df_xlsx = df_barang.to_excel(index=False) # Untuk Streamlit download helper sederhana
        st.download_button(
            label="📥 Download Data Stok ke Excel",
            data=df_barang.to_csv(index=False).encode('utf-8'),
            file_name=f"Ringkasan_Stok_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Belum ada data produk di master barang.")

    # Fitur Edit/Hapus Produk KHUSUS ADMIN
    if st.session_state.role == "admin":
        with st.expander("⚙️ Kelola Produk (Edit / Hapus Produk)"):
            sku_pilih = st.text_input("Masukkan SKU Produk yang ingin diubah/dihapus:")
            if sku_pilih:
                conn = sqlite3.connect("stok_toko.db")
                cursor = conn.cursor()
                cursor.execute("SELECT nama_barang, harga_beli, harga_jual, stok_min FROM barang WHERE sku=?", (sku_pilih,))
                prod_data = cursor.fetchone()
                conn.close()
                
                if prod_data:
                    with st.form("edit_prod_form"):
                        n_nama = st.text_input("Nama Baru", value=prod_data[0])
                        n_hb = st.number_input("Harga Beli Baru", value=float(prod_data[1]))
                        n_hj = st.number_input("Harga Jual Baru", value=float(prod_data[2]))
                        n_stokmin = st.number_input("Stok Min Baru", value=int(prod_data[3]))
                        
                        col_e1, col_e2 = st.columns(2)
                        update_btn = col_e1.form_submit_button("Simpan Perubahan", use_container_width=True)
                        delete_btn = col_e2.form_submit_button("Hapus Produk Ini", use_container_width=True, type="primary")
                        
                        if update_btn:
                            conn = sqlite3.connect("stok_toko.db")
                            cursor = conn.cursor()
                            cursor.execute("UPDATE barang SET nama_barang=?, harga_beli=?, harga_jual=?, stok_min=? WHERE sku=?",
                                           (n_nama, n_hb, n_hj, n_stokmin, sku_pilih))
                            conn.commit()
                            conn.close()
                            st.success(f"Produk SKU {sku_pilih} berhasil diperbarui!")
                            st.rerun()
                            
                        if delete_btn:
                            conn = sqlite3.connect("stok_toko.db")
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM transaksi WHERE sku=?", (sku_pilih,))
                            cursor.execute("DELETE FROM barang WHERE sku=?", (sku_pilih,))
                            conn.commit()
                            conn.close()
                            st.success(f"Produk SKU {sku_pilih} berhasil dihapus!")
                            st.rerun()
                else:
                    st.warning("SKU tidak ditemukan.")


# ================= MENU 2: MASTER BARANG (Admin Only) =================
elif selected_menu == "Master Barang" and st.session_state.role == "admin":
    st.subheader("➕ Tambah Produk Baru")
    
    with st.form("form_tambah_barang"):
        sku = st.text_input("Kode SKU")
        nama_barang = st.text_input("Nama Barang")
        kategori = st.text_input("Kategori")
        harga_beli = st.number_input("Harga Beli (Modal)", min_value=0.0, step=500.0)
        harga_jual = st.number_input("Harga Jual", min_value=0.0, step=500.0)
        stok_min = st.number_input("Stok Minimum Peringatan", min_value=0, value=5)
        
        submitted = st.form_submit_button("Simpan Produk", use_container_width=True)
        if submitted:
            if not sku or not nama_barang:
                st.error("Kode SKU dan Nama Barang wajib diisi!")
            else:
                try:
                    conn = sqlite3.connect("stok_toko.db")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO barang VALUES (?, ?, ?, ?, ?, ?)", 
                                   (sku, nama_barang, kategori, harga_beli, harga_jual, stok_min))
                    conn.commit()
                    conn.close()
                    st.success(f"Produk {nama_barang} berhasil disimpan!")
                except sqlite3.IntegrityError:
                    st.error(f"Kode SKU '{sku}' sudah terdaftar!")


# ================= MENU 3: INPUT TRANSAKSI (Admin Only) =================
elif selected_menu == "Input Transaksi" and st.session_state.role == "admin":
    st.subheader("📝 Catat Transaksi Masuk / Keluar")
    
    conn = sqlite3.connect("stok_toko.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sku, nama_barang FROM barang")
    list_barang = cursor.fetchall()
    conn.close()
    
    if not list_barang:
        st.warning("Belum ada produk terdaftar. Tambahkan produk di menu Master Barang terlebih dahulu.")
    else:
        options_sku = [f"{item[0]} - {item[1]}" for item in list_barang]
        
        with st.form("form_transaksi"):
            tanggal = st.date_input("Tanggal Transaksi", value=datetime.now())
            jenis = st.selectbox("Jenis Transaksi", ["MASUK", "KELUAR"])
            pilih_sku = st.selectbox("Pilih Produk", options_sku)
            jumlah = st.number_input("Jumlah Unit", min_value=1, value=1)
            
            # Ambil default harga
            sku_ambil = pilih_sku.split(" - ")[0]
            conn = sqlite3.connect("stok_toko.db")
            cursor = conn.cursor()
            cursor.execute("SELECT harga_beli, harga_jual FROM barang WHERE sku=?", (sku_ambil,))
            hb, hj = cursor.fetchone()
            conn.close()
            
            def_harga = hb if jenis == "MASUK" else hj
            harga_satuan = st.number_input("Harga Satuan (Rp)", value=float(def_harga), step=500.0)
            keterangan = st.text_input("Keterangan / Supplier / No. Nota")
            
            submit_trx = st.form_submit_button("Simpan Transaksi", use_container_width=True)
            if submit_trx:
                total_harga = jumlah * harga_satuan
                if jenis == "KELUAR":
                    stok_sisa = get_stok_terkini(sku_ambil)
                    if jumlah > stok_sisa:
                        st.error(f"Stok tidak cukup! Stok saat ini: {stok_sisa}")
                        st.stop()
                        
                conn = sqlite3.connect("stok_toko.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transaksi (tanggal, jenis, sku, jumlah, harga_satuan, total_harga, keterangan) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(tanggal), jenis, sku_ambil, jumlah, harga_satuan, total_harga, keterangan))
                conn.commit()
                conn.close()
                st.success(f"Transaksi berhasil dicatat! Total: Rp {total_harga:,.0f}")


# ================= MENU 4: RIWAYAT BARANG MASUK =================
elif selected_menu == "Riwayat Barang Masuk":
    st.subheader("📥 Riwayat Barang Masuk (Restock)")
    
    col_d1, col_d2 = st.columns(2)
    tgl_mulai = col_d1.date_input("Dari Tanggal", value=datetime.strptime("2026-01-01", "%Y-%m-%d"))
    tgl_selesai = col_d2.date_input("Sampai Tanggal", value=datetime.now())
    
    conn = sqlite3.connect("stok_toko.db")
    query = "SELECT id, tanggal, sku, jumlah, harga_satuan, total_harga, keterangan FROM transaksi WHERE jenis='MASUK' AND tanggal BETWEEN ? AND ? ORDER BY id DESC"
    df_masuk = pd.read_sql_query(query, conn, params=(str(tgl_mulai), str(tgl_selesai)), dtype={'id': int})
    conn.close()
    
    if not df_masuk.empty:
        st.dataframe(df_masuk, use_container_width=True)
        
        # Fitur Hapus / Edit Transaksi khusus Admin
        if st.session_state.role == "admin":
            with st.expander("⚙️ Batalkan / Hapus Transaksi Masuk"):
                id_hapus = st.number_input("Masukkan ID Transaksi yang ingin dihapus:", min_value=1, step=1)
                if st.button("Hapus Transaksi Ini"):
                    conn = sqlite3.connect("stok_toko.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM transaksi WHERE id=? AND jenis='MASUK'", (id_hapus,))
                    conn.commit()
                    conn.close()
                    st.success(f"Transaksi Masuk ID {id_hapus} berhasil dihapus!")
                    st.rerun()
    else:
        st.info("Tidak ada riwayat barang masuk pada rentang tanggal tersebut.")


# ================= MENU 5: RIWAYAT BARANG KELUAR =================
elif selected_menu == "Riwayat Barang Keluar":
    st.subheader("📤 Riwayat Barang Keluar (Penjualan)")
    
    col_d1, col_d2 = st.columns(2)
    tgl_mulai = col_d1.date_input("Dari Tanggal ", value=datetime.strptime("2026-01-01", "%Y-%m-%d"))
    tgl_selesai = col_d2.date_input("Sampai Tanggal ", value=datetime.now())
    
    conn = sqlite3.connect("stok_toko.db")
    query = "SELECT id, tanggal, sku, jumlah, harga_satuan, total_harga, keterangan FROM transaksi WHERE jenis='KELUAR' AND tanggal BETWEEN ? AND ? ORDER BY id DESC"
    df_keluar = pd.read_sql_query(query, conn, params=(str(tgl_mulai), str(tgl_selesai)), dtype={'id': int})
    conn.close()
    
    if not df_keluar.empty:
        st.dataframe(df_keluar, use_container_width=True)
        
        if st.session_state.role == "admin":
            with st.expander("⚙️ Batalkan / Hapus Transaksi Keluar"):
                id_hapus = st.number_input("Masukkan ID Transaksi Keluar yang ingin dihapus:", min_value=1, step=1, key="id_keluar_del")
                if st.button("Hapus Transaksi Keluar Ini"):
                    conn = sqlite3.connect("stok_toko.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM transaksi WHERE id=? AND jenis='KELUAR'", (id_hapus,))
                    conn.commit()
                    conn.close()
                    st.success(f"Transaksi Keluar ID {id_hapus} berhasil dihapus!")
                    st.rerun()
    else:
        st.info("Tidak ada riwayat barang keluar pada rentang tanggal tersebut.")


# ================= MENU 6: LAPORAN BARANG TERLARIS (Admin Only) =================
elif selected_menu == "Laporan Barang Terlaris" and st.session_state.role == "admin":
    st.subheader("🏆 Laporan Barang Paling Banyak Terjual (Best Seller)")
    
    col_d1, col_d2 = st.columns(2)
    tgl_mulai = col_d1.date_input("Dari Tanggal  ", value=datetime.strptime("2026-01-01", "%Y-%m-%d"))
    tgl_selesai = col_d2.date_input("Sampai Tanggal  ", value=datetime.now())
    
    conn = sqlite3.connect("stok_toko.db")
    query = """
        SELECT t.sku AS SKU, b.nama_barang AS 'Nama Barang', SUM(t.jumlah) AS 'Total Terjual', SUM(t.total_harga) AS 'Total Pemasukan' 
        FROM transaksi t JOIN barang b ON t.sku = b.sku 
        WHERE t.jenis = 'KELUAR' AND t.tanggal BETWEEN ? AND ? 
        GROUP BY t.sku ORDER BY 'Total Terjual' DESC
    """
    df_terlaris = pd.read_sql_query(query, conn, params=(str(tgl_mulai), str(tgl_selesai)))
    conn.close()
    
    if not df_terlaris.empty:
        st.dataframe(df_terlaris, use_container_width=True)
    else:
        st.info("Tidak ada data penjualan pada rentang tanggal tersebut.")
