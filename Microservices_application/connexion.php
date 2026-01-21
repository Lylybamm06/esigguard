<?php
  $titre = "Connexion";

  include('header.inc.php');
  include('menu.inc.php');
?>

  <h1>Connexion à votre compte</h1>
  <?php
require('fonction.php');
session_start();

if (isset($_POST['email'])){
  $email = stripslashes($_REQUEST['email']);
  $mail = mysqli_real_escape_string($conn, $mail);
  $password = stripslashes($_REQUEST['password']);
  $password = mysqli_real_escape_string($conn, $password);


    $query = "SELECT * FROM `run` WHERE email='$email' and password='$password'";
  $result = mysqli_query($conn,$query) or die(mysql_error());
  $rows = mysqli_num_rows($result);
  if($rows==1){
      $_SESSION['pseudo'] = $pseudo;
      header("Location: PageUtilisateur.php");
  }else{
    $message = "Le nom d'utilisateur ou le mot de passe est incorrect.";
  }
}
?>
 <section class="item">
<form class="box" action="" method="post" name="login">
<h1 class="box-title">Connexion</h1>
<p>Entrer votre mail :<input type="text" class="pseudo" name="email" placeholder="Votre Nom d'utilisateur ou pseudo"></p>
<p>Entrer votre mot de passe :<input type="password" class="password" name="password" placeholder="Mot de passe"></p>
<p><input type="submit" value="Connexion " name="submit" class="Connexion"></p>
<p><a href="Page d'oubli1.php" class="Oublie">Mot de passe oublié?</a></p>
</section>
<?php if (! empty($message)) { ?>
    <p class="errorMessage"><?php echo $message; ?></p>
<?php } ?>
</form>
<?php
  include('footer.inc.php');
?>