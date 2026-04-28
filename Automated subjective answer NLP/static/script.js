
function previewImage() {
  var input = document.getElementById('imageInput');
  var preview = document.getElementById('imagePreview');
  var answersDiv = document.getElementById('answers');

  while (answersDiv.firstChild) {
    answersDiv.removeChild(answersDiv.firstChild);
  }

  if (input.files && input.files[0]) {
    var reader = new FileReader();
    reader.onload = function (e) {
      var img = document.createElement('img');
      img.src = e.target.result;
      preview.innerHTML = '';
      preview.appendChild(img);

      var answers = getAnswersFromImage(input.files[0]);
      displayAnswers(answers);
    };

    reader.readAsDataURL(input.files[0]);
  }
}

function displayAnswers(answers) 
{
  var answersDiv = document.getElementById('answers');

  for (var i = 0; i < answers.length; i++) {
    var answerParagraph = document.createElement('p');
    answerParagraph.textContent = 'Answer ' + (i + 1) + ': ' + answers[i];
    answersDiv.appendChild(answerParagraph);
  }
}
function getAnswersFromImage(imageFile) 
{
  return ['Answer'];
}
/*document.getElementById('evaluateButton').addEventListener('click', function() {
  evaluateAnswers();
});

function evaluateAnswers() {
  console.log("Evaluation logic goes here");
}*/