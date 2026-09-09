-- création de la table etudiants
CREATE TABLE etudiants (
    id SERIAL PRIMARY KEY,
    nom VARCHAR (50),
    prenom VARCHAR (50),
    age INT,
    ville VARCHAR (50)
);

-- insertion des données dans la table etuduiants
INSERT INTO etudiants(nom, prenom, age, ville)
VALUES 
('KAMGA', 'PIERRE', 40, 'Yaoundé'),
('BATIKA', 'thomas',25, 'Douala'),
('OLOMO', 'Idrice', 52, 'Ngaoundéré'),
('ATANGANA', 'Olive', 35, 'Bafoussam');