CREATE DATABASE GestorVentas;
GO

USE GestorVentas;
GO

/* Tabla Ventas */
CREATE TABLE Ventas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    descripcion NVARCHAR(255) NOT NULL,
    cliente NVARCHAR(100) NOT NULL,
    dni NVARCHAR(20) NULL,
    monto DECIMAL(10,2) NOT NULL,
    fecha DATE NOT NULL
);

/* Tabla Usuario */
CREATE TABLE Usuario (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(100) NOT NULL,
    password NVARCHAR(255) NOT NULL
);

/* Usuario inicial */
INSERT INTO Usuario (username, password)
VALUES ('administrador', '13579');

CREATE INDEX IX_Ventas_Agrupaciones
ON Ventas (dni, cliente, fecha) INCLUDE (monto);